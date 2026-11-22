import json
import os
from pathlib import Path

from . import database


class SettingsManager:
    """Manages local JSON application settings with legacy txt migration."""

    def __init__(self, project_root: Path, config_file=None):
        self.project_root = project_root
        self.is_default = config_file is None
        self.config_file = str(config_file or (project_root / "app_settings.json"))
        self.settings: dict = {}

    def load(self) -> tuple[str | None, str | None]:
        """Loads settings from JSON and returns (library_path, db_path)."""
        library_path = None
        db_path = None

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.settings = data
                    path = data.get("library_path")
                    if path and os.path.exists(path):
                        library_path = path
                        db_path = os.path.join(path, "data", "library.db")
                        if os.path.exists(db_path):
                            database.init_db(db_path)
            except Exception:
                self.settings = {}
        elif self.is_default:
            legacy_txt = self.project_root / "app_settings.txt"
            if legacy_txt.exists():
                try:
                    path = legacy_txt.read_text(encoding="utf-8").strip()
                    if path:
                        self.save(path)
                        if os.path.exists(path):
                            library_path = path
                            db_path = os.path.join(path, "data", "library.db")
                            if os.path.exists(db_path):
                                database.init_db(db_path)
                    legacy_txt.unlink(missing_ok=True)
                except Exception:
                    pass

        return library_path, db_path

    def save(self, library_path: str | None = None) -> None:
        """Persists settings as formatted JSON."""
        try:
            if library_path is not None:
                self.settings["library_path"] = library_path
            config_dir = os.path.dirname(self.config_file)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
                f.write("\n")
        except Exception:
            pass

    def as_dict(self) -> dict:
        return dict(self.settings)
