import os
import sys
import tempfile
import unittest
import wave
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from audio_library.api import AudioLibraryAPI, LIBRARY_SUBFOLDERS


def create_silent_wav(path: Path, duration_sec: float = 1.0, sample_rate: int = 8000) -> None:
    """Creates a minimal valid PCM WAV file for testing audio import & duration extraction."""
    num_frames = int(duration_sec * sample_rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_frames)


class TestAudioLibraryAPI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.library_dir = self.root / "library"
        self.config_file = self.root / "app_settings.txt"
        self.api = AudioLibraryAPI(config_file=self.config_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_unconfigured_status_before_init(self):
        self.assertEqual(self.api.get_library_status()["status"], "unconfigured")
        self.assertEqual(self.api.get_songs(), [])

    def test_initialize_library_creates_folders_and_persists_settings(self):
        res = self.api.initialize_library(str(self.library_dir))
        self.assertEqual(res["status"], "success")
        self.assertEqual(self.api.get_library_status()["status"], "configured")

        for folder in LIBRARY_SUBFOLDERS:
            self.assertTrue((self.library_dir / folder).is_dir())
        self.assertTrue((self.library_dir / "data" / "library.db").is_file())
        self.assertEqual(self.config_file.read_text(encoding="utf-8").strip(), str(self.library_dir))

    def test_artist_album_and_song_lifecycle(self):
        self.api.initialize_library(str(self.library_dir))

        # Create artist with avatar
        avatar_src = self.root / "avatar.png"
        avatar_src.write_bytes(b"fake-png")
        artist_res = self.api.create_artist(
            {
                "name": "Claude Debussy",
                "real_name": "Achille-Claude Debussy",
                "dob": "1862-08-22",
                "aliases": ["Debussy", "クロード・ドビュッシー"],
                "avatar_file_src": str(avatar_src),
            }
        )
        self.assertEqual(artist_res["status"], "success")
        artist_slug = artist_res["slug"]

        # Create album with cover
        cover_src = self.root / "cover.jpg"
        cover_src.write_bytes(b"fake-jpg")
        album_res = self.api.create_album(
            {
                "name": "Suite Bergamasque",
                "artist_slug": artist_slug,
                "release_date": "1905-01-01",
                "cover_file_src": str(cover_src),
            }
        )
        self.assertEqual(album_res["status"], "success")

        # Verify metadata options return full artist/album details
        options = self.api.get_metadata_options()
        self.assertEqual(len(options["artists"]), 1)
        self.assertEqual(options["artists"][0]["avatar_image"], f"artist/{artist_slug}/avatar.png")
        self.assertEqual(len(options["albums"]), 1)
        self.assertTrue(options["albums"][0]["album_cover"].endswith("cover.jpg"))

        # Import two tracks with identical names to verify collision handling & duration reading
        wav_src = self.root / "clair_de_lune.wav"
        create_silent_wav(wav_src, duration_sec=2.0)

        import_1 = self.api.import_song(
            str(wav_src),
            {
                "song_name": "Clair de Lune",
                "main_artists": [artist_slug],
                "featured_artists": ["Guest Soloist"],
                "album_slug": "Suite Bergamasque",
                "key": "D#",
                "scale": "Minor",
                "tempo": 66,
                "genres": ["Classical", "Impressionist"],
            },
        )
        self.assertEqual(import_1["status"], "success")
        self.assertEqual(import_1["song_file"], "Clair_de_Lune.wav")

        import_2 = self.api.import_song(
            str(wav_src),
            {
                "song_name": "Clair de Lune",
                "main_artists": ["Claude Debussy"],
            },
        )
        self.assertEqual(import_2["status"], "success")
        self.assertEqual(import_2["song_file"], "Clair_de_Lune_1.wav")

        # Query songs & verify SQL joins and duration
        songs = self.api.get_songs()
        self.assertEqual(len(songs), 2)
        first = next(s for s in songs if s["song_file"] == "Clair_de_Lune.wav")
        self.assertAlmostEqual(first["duration"], 2.0, places=1)
        self.assertEqual(first["key_name"], "D#")
        self.assertEqual(first["scale_name"], "Minor")
        self.assertEqual(first["main_artists_slugs"], artist_slug)
        self.assertEqual(first["feat_artists"], "Guest Soloist")
        self.assertIn("Classical", first["genres"])
        self.assertIn("Impressionist", first["genres"])

        # Update song metadata
        upd = self.api.update_song(
            "Clair_de_Lune.wav",
            {
                "song_name": "Clair de Lune (Remastered)",
                "main_artists": [artist_slug],
                "featured_artists": [],
                "album_slug": "Suite Bergamasque",
                "track_number": 3,
                "key": "C#",
                "scale": "Major",
                "tempo": 68,
                "genres": ["Classical"],
            },
        )
        self.assertEqual(upd["status"], "success")

        updated_first = next(s for s in self.api.get_songs() if s["song_file"] == "Clair_de_Lune.wav")
        self.assertEqual(updated_first["song_name"], "Clair de Lune (Remastered)")
        self.assertEqual(updated_first["track_number"], 3)
        self.assertEqual(updated_first["tempo"], 68)

        # Stats check
        stats = self.api.get_stats()
        self.assertEqual(stats["songs"], 2)
        self.assertEqual(stats["artists"], 2)  # Debussy + auto-created Guest Soloist
        self.assertEqual(stats["albums"], 1)


if __name__ == "__main__":
    unittest.main()
