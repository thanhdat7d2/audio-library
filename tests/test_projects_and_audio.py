import unittest

from tests.helpers import BaseLibraryTestCase, create_silent_wav


class TestProjectsAndMetadataOnlySongs(BaseLibraryTestCase):
    def test_add_song_without_audio_and_attach_later(self):
        self.api.initialize_library(str(self.library_dir))

        res1 = self.api.add_song(
            {
                "song_name": "Future Single",
                "main_artists": ["Indie Producer"],
                "genres": ["Synthwave"],
                "tags": ["AI Generated", "WIP"],
                "tempo": 124,
            }
        )
        self.assertEqual(res1["status"], "success")
        self.assertFalse(res1["has_audio"])
        self.assertIsNone(res1["audio_file"])

        res2 = self.api.add_song({"song_name": "Future Single"})
        self.assertEqual(res2["status"], "success")
        self.assertNotEqual(res1["song_file"], res2["song_file"])

        stats = self.api.get_stats()
        self.assertEqual(stats["songs"], 2)
        self.assertEqual(stats["songs_without_audio"], 2)

        wav_src = self.root / "future_single_master.wav"
        create_silent_wav(wav_src, duration_sec=1.5)
        attach = self.api.attach_song_audio(res1["song_file"], str(wav_src))
        self.assertEqual(attach["status"], "success")
        self.assertAlmostEqual(attach["duration"], 1.5, places=1)

        song = next(s for s in self.api.get_songs() if s["song_file"] == res1["song_file"])
        self.assertEqual(song["has_audio"], 1)
        self.assertEqual(song["audio_file"], attach["audio_file"])
        self.assertIn("AI Generated", song["tags"])
        self.assertIn("WIP", song["tags"])
        self.assertTrue((self.library_dir / "song" / attach["audio_file"]).is_file())
        self.assertEqual(self.api.get_stats()["songs_without_audio"], 1)

    def test_production_projects_on_song_artist_and_album(self):
        self.api.initialize_library(str(self.library_dir))

        proj_dir = self.root / "daw_projects" / "my_remix"
        proj_dir.mkdir(parents=True)

        artist_res = self.api.create_artist({"name": "Daft Punk", "project_path": str(proj_dir)})
        album_res = self.api.create_album(
            {"name": "Discovery", "artist_slug": artist_res["slug"], "project_path": str(proj_dir)}
        )
        song_res = self.api.add_song(
            {
                "song_name": "Aerodynamic",
                "main_artists": [artist_res["slug"]],
                "album_slug": album_res["slug"],
                "project_path": str(proj_dir),
                "project_name": "Aerodynamic FLP",
            }
        )

        all_projects = self.api.get_projects()
        self.assertEqual(len(all_projects), 3)
        by_type = {p["entity_type"]: p for p in all_projects}
        self.assertEqual(by_type["song"]["project_name"], "Aerodynamic FLP")
        self.assertEqual(by_type["song"]["entity_label"], "Aerodynamic")
        self.assertTrue(by_type["song"]["path_exists"])
        self.assertEqual(by_type["artist"]["entity_label"], "Daft Punk")
        self.assertEqual(by_type["album"]["entity_label"], "Discovery")

        song_proj_id = by_type["song"]["id"]
        upd = self.api.update_project(
            song_proj_id,
            {
                "entity_type": "song",
                "entity_id": song_res["song_file"],
                "project_name": "Aerodynamic VIP Mix",
                "project_path": str(proj_dir),
                "notes": "123 BPM Ableton project",
            },
        )
        self.assertEqual(upd["status"], "success")
        song_projects = self.api.get_projects("song", song_res["song_file"])
        self.assertEqual(song_projects[0]["project_name"], "Aerodynamic VIP Mix")
        self.assertEqual(song_projects[0]["notes"], "123 BPM Ableton project")

        self.assertEqual(self.api.get_songs()[0]["project_count"], 1)
        options = self.api.get_metadata_options()
        self.assertEqual(options["artists"][0]["project_count"], 1)
        self.assertEqual(options["albums"][0]["project_count"], 1)

        del_res = self.api.delete_project(song_proj_id)
        self.assertEqual(del_res["status"], "success")
        self.assertEqual(len(self.api.get_projects("song", song_res["song_file"])), 0)


if __name__ == "__main__":
    unittest.main()
