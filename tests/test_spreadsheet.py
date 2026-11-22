import csv
import unittest

import openpyxl

from tests.helpers import BaseLibraryTestCase, create_silent_wav


class TestSpreadsheetImport(BaseLibraryTestCase):
    def test_spreadsheet_import_csv_template_and_xlsx(self):
        self.api.initialize_library(str(self.library_dir))

        wav_src = self.root / "sample_track.wav"
        create_silent_wav(wav_src, duration_sec=1.0)
        proj_dir = self.root / "ableton_proj"
        proj_dir.mkdir()

        csv_path = self.root / "tracks.csv"
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Title", "Artists", "Featured", "Album", "Genres", "Tags",
                "AI Generated", "Key", "Scale", "BPM", "Audio File", "Project Path",
            ])
            writer.writerow([
                "AI Dreamscape", "Neural Synth", "", "Synthetic Vol 1", "Ambient; Electronic", "Demo",
                "yes", "C", "Minor", "95", "", str(proj_dir),
            ])
            writer.writerow([
                "Real Recording", "Acoustic Duo", "Cellist", "Live Session", "Folk", "Live",
                "false", "G", "Major", "110", str(wav_src), "",
            ])

        preview = self.api.preview_spreadsheet(str(csv_path))
        self.assertEqual(preview["status"], "success")
        self.assertEqual(preview["total_rows"], 2)

        res = self.api.import_songs_from_spreadsheet(str(csv_path))
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["imported"], 2)
        self.assertEqual(res["with_audio"], 1)
        self.assertEqual(res["without_audio"], 1)
        self.assertEqual(res["failed"], 0)

        songs = {s["song_name"]: s for s in self.api.get_songs()}
        self.assertEqual(songs["AI Dreamscape"]["has_audio"], 0)
        self.assertIn("AI Generated", songs["AI Dreamscape"]["tags"])
        self.assertIn("Demo", songs["AI Dreamscape"]["tags"])
        self.assertEqual(songs["AI Dreamscape"]["project_count"], 1)

        self.assertEqual(songs["Real Recording"]["has_audio"], 1)
        self.assertAlmostEqual(songs["Real Recording"]["duration"], 1.0, places=1)
        self.assertEqual(songs["Real Recording"]["feat_artists"], "Cellist")

        tpl_path = self.root / "template.csv"
        tpl_res = self.api.export_spreadsheet_template(str(tpl_path))
        self.assertEqual(tpl_res["status"], "success")
        self.assertTrue(tpl_path.is_file())

        xlsx_path = self.root / "tracks.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["song_name", "main_artists", "tags", "ai_generated", "tempo"])
        ws.append(["Excel Track", "Spreadsheet Artist", "Remix", True, 128])
        wb.save(xlsx_path)

        xlsx_res = self.api.import_songs_from_spreadsheet(str(xlsx_path))
        self.assertEqual(xlsx_res["status"], "success")
        self.assertEqual(xlsx_res["imported"], 1)
        self.assertEqual(xlsx_res["without_audio"], 1)

        excel_song = next(s for s in self.api.get_songs() if s["song_name"] == "Excel Track")
        self.assertIn("AI Generated", excel_song["tags"])
        self.assertIn("Remix", excel_song["tags"])
        self.assertEqual(excel_song["tempo"], 128)


if __name__ == "__main__":
    unittest.main()
