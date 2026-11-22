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
                for expected in ("songs", "artists", "artist_names", "albums", "genres", "keys", "scales", "config"):
                    self.assertIn(expected, tables)

                keys_count = conn.execute("SELECT COUNT(*) FROM keys").fetchone()[0]
                scales_count = conn.execute("SELECT COUNT(*) FROM scales").fetchone()[0]
                genres_count = conn.execute("SELECT COUNT(*) FROM genres").fetchone()[0]
                countries_count = conn.execute("SELECT COUNT(*) FROM countries").fetchone()[0]

                self.assertEqual(keys_count, 12)
                self.assertEqual(scales_count, 12)
                self.assertEqual(genres_count, 12)
                self.assertEqual(countries_count, 10)
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
