import json
import unittest

from tests.helpers import BaseLibraryTestCase, create_silent_wav
from audio_library.api import AudioLibraryAPI, LIBRARY_SUBFOLDERS
from audio_library.app import render_index_html


class TestAudioLibraryAPI(BaseLibraryTestCase):
    def test_unconfigured_status_before_init(self):
        self.assertEqual(self.api.get_library_status()["status"], "unconfigured")
        self.assertEqual(self.api.get_songs(), [])

    def test_initialize_library_creates_folders_and_persists_json_settings(self):
        res = self.api.initialize_library(str(self.library_dir))
        self.assertEqual(res["status"], "success")
        self.assertEqual(self.api.get_library_status()["status"], "configured")

        for folder in LIBRARY_SUBFOLDERS:
            self.assertTrue((self.library_dir / folder).is_dir())
        self.assertTrue((self.library_dir / "data" / "library.db").is_file())

        saved_json = json.loads(self.config_file.read_text(encoding="utf-8"))
        self.assertEqual(saved_json["library_path"], str(self.library_dir))

        reloaded = AudioLibraryAPI(config_file=self.config_file)
        self.assertEqual(reloaded.get_library_status()["status"], "configured")
        self.assertEqual(reloaded.library_path, str(self.library_dir))

    def test_artist_album_and_song_lifecycle_with_tags(self):
        self.api.initialize_library(str(self.library_dir))

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

        options = self.api.get_metadata_options()
        self.assertEqual(len(options["artists"]), 1)
        self.assertEqual(options["artists"][0]["avatar_image"], f"artist/{artist_slug}/avatar.png")
        self.assertEqual(len(options["albums"]), 1)
        self.assertTrue(options["albums"][0]["album_cover"].endswith("cover.jpg"))
        self.assertIn("AI Generated", [t["tag_name"] for t in options["tags"]])

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
                "tags": ["AI Generated", "Piano Solo"],
            },
        )
        self.assertEqual(import_1["status"], "success")
        self.assertEqual(import_1["song_file"], "Clair_de_Lune.wav")
        self.assertTrue(import_1["has_audio"])

        import_2 = self.api.import_song(
            str(wav_src),
            {
                "song_name": "Clair de Lune",
                "main_artists": ["Claude Debussy"],
                "ai_generated": True,
            },
        )
        self.assertEqual(import_2["status"], "success")
        self.assertEqual(import_2["song_file"], "Clair_de_Lune_1.wav")

        songs = self.api.get_songs()
        self.assertEqual(len(songs), 2)
        first = next(s for s in songs if s["song_file"] == "Clair_de_Lune.wav")
        self.assertAlmostEqual(first["duration"], 2.0, places=1)
        self.assertEqual(first["has_audio"], 1)
        self.assertEqual(first["audio_file"], "Clair_de_Lune.wav")
        self.assertEqual(first["key_name"], "D#")
        self.assertEqual(first["scale_name"], "Minor")
        self.assertEqual(first["main_artists_slugs"], artist_slug)
        self.assertEqual(first["feat_artists"], "Guest Soloist")
        self.assertIn("Classical", first["genres"])
        self.assertIn("Impressionist", first["genres"])
        self.assertIn("AI Generated", first["tags"])
        self.assertIn("Piano Solo", first["tags"])

        second = next(s for s in songs if s["song_file"] == "Clair_de_Lune_1.wav")
        self.assertIn("AI Generated", second["tags"])

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
                "tags": ["Mastered"],
            },
        )
        self.assertEqual(upd["status"], "success")

        updated_first = next(s for s in self.api.get_songs() if s["song_file"] == "Clair_de_Lune.wav")
        self.assertEqual(updated_first["song_name"], "Clair de Lune (Remastered)")
        self.assertEqual(updated_first["track_number"], 3)
        self.assertEqual(updated_first["tempo"], 68)
        self.assertEqual(updated_first["tags"], "Mastered")

        stats = self.api.get_stats()
        self.assertEqual(stats["songs"], 2)
        self.assertEqual(stats["artists"], 2)
        self.assertEqual(stats["albums"], 1)

    def test_render_index_html_inlines_partials(self):
        html = render_index_html()
        self.assertIn('id="view-dashboard"', html)
        self.assertIn('id="view-import"', html)
        self.assertIn('id="view-settings"', html)
        self.assertIn('id="modal-project"', html)
        self.assertIn('id="player-waveform-canvas"', html)
        self.assertNotIn("DECK MANAGER", html)
        self.assertNotIn("<!-- include:", html)

    def test_update_settings_persists_theme_and_library_path(self):
        res = self.api.update_settings({"theme": "midnight-violet", "library_path": str(self.library_dir)})
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["settings"]["theme"], "midnight-violet")
        self.assertEqual(res["settings"]["library_path"], str(self.library_dir))

        reloaded = AudioLibraryAPI(config_file=self.config_file)
        self.assertEqual(reloaded.get_settings()["theme"], "midnight-violet")
        self.assertEqual(reloaded.library_path, str(self.library_dir))


if __name__ == "__main__":
    unittest.main()
