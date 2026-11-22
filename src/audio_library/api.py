import os
from pathlib import Path

from . import database
from .services import catalog, dialogs, projects, resolvers, songs, spreadsheet
from .settings import SettingsManager

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LIBRARY_SUBFOLDERS = (
    "data",
    "song",
    "samplepack",
    "looppack",
    "artist",
    "album",
    "mixtape",
    "stem",
)


class AudioLibraryAPI:
    """Thin pywebview JS-to-Python API bridge delegating to domain service modules."""

    def __init__(self, config_file=None):
        self._settings = SettingsManager(PROJECT_ROOT, config_file=config_file)
        self.config_file = self._settings.config_file
        self.library_path, self.db_path = self._settings.load()

    def _require_library(self):
        if not self.db_path:
            return {"status": "error", "message": "Library not initialized"}
        return None

    # --- Settings & Library Lifecycle ---

    def get_settings(self):
        return self._settings.as_dict()

    def initialize_library(self, path):
        try:
            for folder in LIBRARY_SUBFOLDERS:
                os.makedirs(os.path.join(path, folder), exist_ok=True)
            db_path = os.path.join(path, "data", "library.db")
            database.init_db(db_path)
            self.library_path = path
            self.db_path = db_path
            self._settings.save(path)
            return {"status": "success", "library_path": path}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def select_library_folder(self):
        folder = dialogs.select_folder()
        if folder:
            return self.initialize_library(folder)
        return {"status": "cancelled"}

    def get_library_status(self):
        if self.library_path and os.path.exists(self.library_path):
            return {"status": "configured", "library_path": self.library_path}
        return {"status": "unconfigured"}

    # --- Native File / Folder Dialogs ---

    def select_file_to_import(self):
        return dialogs.select_import_file()

    def select_project_folder(self):
        return dialogs.select_folder()

    def select_project_file(self):
        return dialogs.select_project_file()

    def select_spreadsheet_file(self):
        return dialogs.select_spreadsheet_file()

    # --- Metadata & Stats ---

    def get_audio_duration(self, file_path):
        return resolvers.get_audio_duration(file_path)

    def get_metadata_options(self):
        return catalog.get_metadata_options(self.db_path) if self.db_path else {}

    def get_stats(self):
        if not self.db_path:
            return {
                "songs": 0, "artists": 0, "albums": 0, "genres": 0,
                "tags": 0, "projects": 0, "songs_without_audio": 0,
            }
        return catalog.get_stats(self.db_path)

    # --- Catalog Entities ---

    def create_artist(self, artist_data):
        return self._require_library() or catalog.create_artist(self.db_path, self.library_path, artist_data)

    def update_artist(self, slug, artist_data):
        return self._require_library() or catalog.update_artist(self.db_path, self.library_path, slug, artist_data)

    def create_album(self, album_data):
        return self._require_library() or catalog.create_album(self.db_path, self.library_path, album_data)

    def update_album(self, slug, album_data):
        return self._require_library() or catalog.update_album(self.db_path, self.library_path, slug, album_data)

    def create_genre(self, name, parent_id=None):
        return self._require_library() or catalog.create_genre(self.db_path, name, parent_id)

    def create_mood(self, name):
        return self._require_library() or catalog.create_mood(self.db_path, name)

    def create_tag(self, name):
        return self._require_library() or catalog.create_tag(self.db_path, name)

    # --- Songs ---

    def add_song(self, song_data, file_path=None):
        return self.import_song(file_path, song_data)

    def import_song(self, file_path, song_data):
        return self._require_library() or songs.import_song(self.db_path, self.library_path, file_path, song_data)

    def attach_song_audio(self, song_file, file_path):
        return self._require_library() or songs.attach_song_audio(self.db_path, self.library_path, song_file, file_path)

    def update_song(self, song_file, song_data):
        return self._require_library() or songs.update_song(self.db_path, self.library_path, song_file, song_data)

    def get_songs(self, filters=None):
        return songs.get_songs(self.db_path) if self.db_path else []

    # --- Production Projects ---

    def create_project(self, project_data):
        return self._require_library() or projects.create_project(self.db_path, project_data)

    def update_project(self, project_id, project_data):
        return self._require_library() or projects.update_project(self.db_path, project_id, project_data)

    def delete_project(self, project_id):
        return self._require_library() or projects.delete_project(self.db_path, project_id)

    def get_projects(self, entity_type=None, entity_id=None):
        return projects.get_projects(self.db_path, entity_type, entity_id) if self.db_path else []

    def open_project_path(self, project_path):
        return projects.open_project_path(project_path)

    # --- Spreadsheet Import ---

    def preview_spreadsheet(self, file_path):
        return spreadsheet.preview_spreadsheet(file_path)

    def import_songs_from_spreadsheet(self, file_path):
        return self._require_library() or spreadsheet.import_songs_from_spreadsheet(
            self.db_path, self.library_path, file_path
        )

    def export_spreadsheet_template(self, dest_path=None):
        if not dest_path:
            dest_path = dialogs.save_csv_file()
            if not dest_path:
                return {"status": "cancelled"}
        return spreadsheet.write_template_csv(dest_path)
