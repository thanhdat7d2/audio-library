import os
import sys
import tempfile
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from audio_library.slug_engine import generate_unique_slug, slugify, transliterate_cyrillic


class TestSlugEngine(unittest.TestCase):
    def test_basic_english_slug(self):
        self.assertEqual(slugify("Moonlight Sonata - Op. 27"), "Moonlight_Sonata_Op_27")

    def test_vietnamese_diacritics_and_d_stroke(self):
        self.assertEqual(slugify("Đêm Đông Hà Nội"), "Dem_Dong_Ha_Noi")
        self.assertEqual(slugify("đàn bầu"), "dan_bau")

    def test_cyrillic_transliteration(self):
        self.assertEqual(transliterate_cyrillic("Чайковский"), "Chajkovskij")
        self.assertEqual(slugify("Пётр Чайковский"), "Pyotr_Chajkovskij")

    def test_cjk_hex_fallback(self):
        slug = slugify("東京")
        self.assertTrue(slug.isascii())
        self.assertRegex(slug, r"^[A-Za-z0-9_]+$")
        self.assertNotEqual(slug, "unknown")

    def test_empty_and_punctuation_only(self):
        self.assertEqual(slugify(""), "empty")
        self.assertEqual(slugify("!!!@@@###"), "unknown")

    def test_unique_slug_for_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "Claude_Debussy"))
            os.makedirs(os.path.join(tmpdir, "claude_debussy_1"))

            result = generate_unique_slug("Claude Debussy", tmpdir)
            self.assertEqual(result, "Claude_Debussy_2")

    def test_unique_slug_with_file_extension(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "Track_One.wav").write_bytes(b"")
            Path(tmpdir, "track_one_1.wav").write_bytes(b"")

            result = generate_unique_slug("Track One", tmpdir, extension=".wav")
            self.assertEqual(result, "Track_One_2")


if __name__ == "__main__":
    unittest.main()
