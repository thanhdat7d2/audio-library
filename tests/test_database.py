import sys
import tempfile
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from audio_library import database


class TestDatabase(unittest.TestCase):
    def test_init_db_creates_schema_and_seed_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "data" / "library.db")
            database.init_db(db_path)

            conn = database.get_db_connection(db_path)
            try:
                tables = {
                    row["name"]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                for expected in (
                    "songs", "artists", "artist_names", "albums", "genres",
                    "keys", "scales", "config", "tags", "song_tags", "projects",
                ):
                    self.assertIn(expected, tables)

                keys_count = conn.execute("SELECT COUNT(*) FROM keys").fetchone()[0]
                scales_count = conn.execute("SELECT COUNT(*) FROM scales").fetchone()[0]
                genres_count = conn.execute("SELECT COUNT(*) FROM genres").fetchone()[0]
                countries_count = conn.execute("SELECT COUNT(*) FROM countries").fetchone()[0]
                tag_names = {row["tag_name"] for row in conn.execute("SELECT tag_name FROM tags").fetchall()}

                self.assertEqual(keys_count, 12)
                self.assertEqual(scales_count, 12)
                self.assertEqual(genres_count, 12)
                self.assertEqual(countries_count, 10)
                self.assertIn("AI Generated", tag_names)
                self.assertGreaterEqual(len(tag_names), 5)
            finally:
                conn.close()

    def test_init_db_migrates_legacy_songs_table(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "legacy.db")
            conn = database.get_db_connection(db_path)
            conn.execute(
                "CREATE TABLE songs (song_file TEXT PRIMARY KEY, song_name TEXT NOT NULL, duration REAL);"
            )
            conn.execute(
                "INSERT INTO songs (song_file, song_name, duration) VALUES ('old_track.mp3', 'Old Track', 120.0);"
            )
            conn.commit()
            conn.close()

            database.init_db(db_path)

            conn = database.get_db_connection(db_path)
            try:
                row = conn.execute("SELECT song_file, has_audio, audio_file FROM songs").fetchone()
                self.assertEqual(row["has_audio"], 1)
                self.assertEqual(row["audio_file"], "old_track.mp3")
            finally:
                conn.close()

    def test_config_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "library.db")
            database.init_db(db_path)

            self.assertIsNone(database.get_config(db_path, "theme"))
            database.set_config(db_path, "theme", "dark")
            self.assertEqual(database.get_config(db_path, "theme"), "dark")


if __name__ == "__main__":
    unittest.main()
