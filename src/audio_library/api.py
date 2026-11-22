import os
import shutil
from pathlib import Path

import webview
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE

from . import database
from .slug_engine import generate_unique_slug

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
    """Python backend API exposed to the WebView frontend via window.pywebview.api."""

    def __init__(self, config_file=None):
        self.library_path = None
        self.db_path = None
        self.config_file = str(config_file or (PROJECT_ROOT / "app_settings.txt"))
        self.load_settings()

    def load_settings(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    path = f.read().strip()
                    if path and os.path.exists(path):
                        self.library_path = path
                        self.db_path = os.path.join(path, "data", "library.db")
            except Exception:
                pass

    def save_settings(self, path):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                f.write(path)
        except Exception:
            pass

    def initialize_library(self, path):
        """Creates required library directories, initializes SQLite DB, and persists settings."""
        try:
            for folder in LIBRARY_SUBFOLDERS:
                os.makedirs(os.path.join(path, folder), exist_ok=True)

            db_path = os.path.join(path, "data", "library.db")
            database.init_db(db_path)

            self.library_path = path
            self.db_path = db_path
            self.save_settings(path)

            return {"status": "success", "library_path": path}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def select_library_folder(self):
        """Opens a native folder dialog to choose the library root directory."""
        active_window = webview.active_window()
        if not active_window:
            return {"status": "error", "message": "No active window"}

        result = active_window.create_file_dialog(webview.FOLDER_DIALOG)
        if result and len(result) > 0:
            return self.initialize_library(result[0])
        return {"status": "cancelled"}

    def get_library_status(self):
        """Returns the current library path if configured, or unconfigured."""
        if self.library_path and os.path.exists(self.library_path):
            return {"status": "configured", "library_path": self.library_path}
        return {"status": "unconfigured"}

    def get_audio_duration(self, file_path):
        """Reads audio duration in seconds using mutagen."""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext == ".mp3":
                return MP3(file_path).info.length
            if ext == ".wav":
                return WAVE(file_path).info.length
            if ext == ".flac":
                return FLAC(file_path).info.length
            if ext in (".ogg", ".ogv"):
                return OggVorbis(file_path).info.length
            return 0.0
        except Exception:
            return 0.0

    def get_metadata_options(self):
        """Fetches reference metadata lists (keys, scales, genres, moods, artists, albums, countries)."""
        if not self.db_path:
            return {}
        conn = database.get_db_connection(self.db_path)
        try:
            keys = [row["key_name"] for row in conn.execute("SELECT key_name FROM keys").fetchall()]
            scales = [row["scale_name"] for row in conn.execute("SELECT scale_name FROM scales").fetchall()]
            genres = [dict(row) for row in conn.execute("SELECT id, genre_name FROM genres").fetchall()]
            moods = [dict(row) for row in conn.execute("SELECT id, mood_name FROM moods").fetchall()]
            artists = [
                dict(row)
                for row in conn.execute(
                    "SELECT slug, real_name, date_of_birth, country_id, avatar_image FROM artists"
                ).fetchall()
            ]
            albums = [
                dict(row)
                for row in conn.execute(
                    "SELECT slug, album_name, release_date, album_cover, artist_slug FROM albums"
                ).fetchall()
            ]
            countries = [dict(row) for row in conn.execute("SELECT id, country_name FROM countries").fetchall()]

            return {
                "keys": keys,
                "scales": scales,
                "genres": genres,
                "moods": moods,
                "artists": artists,
                "albums": albums,
                "countries": countries,
            }
        finally:
            conn.close()

    def select_file_to_import(self):
        """Opens a native file dialog to choose a file for import."""
        active_window = webview.active_window()
        if not active_window:
            return None
        file_types = (
            "All files (*.*)",
            "Audio files (*.mp3;*.wav;*.flac;*.ogg)",
            "Images (*.jpg;*.jpeg;*.png;*.webp)",
        )
        result = active_window.create_file_dialog(webview.OPEN_DIALOG, file_types=file_types)
        return result[0] if result else None

    def create_artist(self, artist_data):
        """Creates an artist record and corresponding asset directory."""
        if not self.db_path:
            return {"status": "error", "message": "Library not initialized"}

        name = artist_data.get("name", "").strip()
        real_name = artist_data.get("real_name", "").strip() or name
        dob = artist_data.get("dob", "").strip()
        country_id = artist_data.get("country_id")

        if not name:
            return {"status": "error", "message": "Artist name is required"}

        conn = database.get_db_connection(self.db_path)
        try:
            slug = generate_unique_slug(name, os.path.join(self.library_path, "artist"))
            artist_dir = os.path.join(self.library_path, "artist", slug)
            os.makedirs(artist_dir, exist_ok=True)

            avatar_path = ""
            avatar_file_src = artist_data.get("avatar_file_src")
            if avatar_file_src and os.path.exists(avatar_file_src):
                ext = os.path.splitext(avatar_file_src)[1]
                avatar_filename = f"avatar{ext}"
                shutil.copy2(avatar_file_src, os.path.join(artist_dir, avatar_filename))
                avatar_path = f"artist/{slug}/{avatar_filename}"

            conn.execute(
                "INSERT INTO artists (slug, real_name, date_of_birth, country_id, avatar_image) VALUES (?, ?, ?, ?, ?)",
                (slug, real_name, dob, country_id, avatar_path),
            )
            conn.execute(
                "INSERT INTO artist_names (artist_slug, name) VALUES (?, ?)",
                (slug, name),
            )

            for alias in artist_data.get("aliases", []):
                alias = alias.strip()
                if alias and alias != name:
                    conn.execute(
                        "INSERT OR IGNORE INTO artist_names (artist_slug, name) VALUES (?, ?)",
                        (slug, alias),
                    )

            conn.commit()
            return {"status": "success", "slug": slug, "name": name}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()

    def create_album(self, album_data):
        """Creates an album record and corresponding asset directory."""
        if not self.db_path:
            return {"status": "error", "message": "Library not initialized"}

        name = album_data.get("name", "").strip()
        release_date = album_data.get("release_date", "").strip()
        artist_slug = album_data.get("artist_slug")

        if not name:
            return {"status": "error", "message": "Album name is required"}

        conn = database.get_db_connection(self.db_path)
        try:
            slug = generate_unique_slug(name, os.path.join(self.library_path, "album"))
            album_dir = os.path.join(self.library_path, "album", slug)
            os.makedirs(album_dir, exist_ok=True)

            cover_path = ""
            cover_file_src = album_data.get("cover_file_src")
            if cover_file_src and os.path.exists(cover_file_src):
                ext = os.path.splitext(cover_file_src)[1]
                cover_filename = f"cover{ext}"
                shutil.copy2(cover_file_src, os.path.join(album_dir, cover_filename))
                cover_path = f"album/{slug}/{cover_filename}"

            conn.execute(
                "INSERT INTO albums (slug, album_name, release_date, album_cover, artist_slug) VALUES (?, ?, ?, ?, ?)",
                (slug, name, release_date, cover_path, artist_slug),
            )
            conn.commit()
            return {"status": "success", "slug": slug, "name": name}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()

    def create_genre(self, name, parent_id=None):
        if not self.db_path:
            return {"status": "error", "message": "Library not initialized"}
        conn = database.get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO genres (genre_name, sub_genre_of) VALUES (?, ?)", (name.strip(), parent_id))
            conn.commit()
            return {"status": "success", "id": cursor.lastrowid}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()

    def create_mood(self, name):
        if not self.db_path:
            return {"status": "error", "message": "Library not initialized"}
        conn = database.get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO moods (mood_name) VALUES (?)", (name.strip(),))
            conn.commit()
            return {"status": "success", "id": cursor.lastrowid}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()

    def resolve_artist_slugs(self, conn, artist_identifiers):
        """Resolves artist slugs or names, auto-creating missing artists on the fly."""
        slugs = []
        for ident in artist_identifiers:
            if not ident:
                continue
            ident = str(ident).strip()
            if not ident:
                continue

            row = conn.execute("SELECT slug FROM artists WHERE slug = ?", (ident,)).fetchone()
            if row:
                slugs.append(row["slug"])
                continue

            row = conn.execute("SELECT artist_slug FROM artist_names WHERE name LIKE ?", (ident,)).fetchone()
            if row:
                slugs.append(row["artist_slug"])
                continue

            new_slug = generate_unique_slug(ident, os.path.join(self.library_path, "artist"))
            os.makedirs(os.path.join(self.library_path, "artist", new_slug), exist_ok=True)

            conn.execute("INSERT INTO artists (slug, real_name) VALUES (?, ?)", (new_slug, ident))
            conn.execute("INSERT INTO artist_names (artist_slug, name) VALUES (?, ?)", (new_slug, ident))
            slugs.append(new_slug)
        return slugs

    def resolve_album_slug(self, conn, album_identifier, main_artist_slugs=None):
        """Resolves an album slug or name, auto-creating a missing album on the fly."""
        if not album_identifier:
            return None
        album_identifier = str(album_identifier).strip()
        if not album_identifier:
            return None

        row = conn.execute("SELECT slug FROM albums WHERE slug = ?", (album_identifier,)).fetchone()
        if row:
            return row["slug"]

        row = conn.execute("SELECT slug FROM albums WHERE album_name LIKE ?", (album_identifier,)).fetchone()
        if row:
            return row["slug"]

        new_slug = generate_unique_slug(album_identifier, os.path.join(self.library_path, "album"))
        os.makedirs(os.path.join(self.library_path, "album", new_slug), exist_ok=True)

        artist_slug = main_artist_slugs[0] if main_artist_slugs else None
        conn.execute(
            "INSERT INTO albums (slug, album_name, artist_slug) VALUES (?, ?, ?)",
            (new_slug, album_identifier, artist_slug),
        )
        return new_slug

    def resolve_genre_ids(self, conn, genre_identifiers):
        """Resolves genre IDs or names, auto-creating missing genres on the fly."""
        ids = []
        for ident in genre_identifiers:
            if not ident:
                continue
            if isinstance(ident, int) or (isinstance(ident, str) and ident.isdigit()):
                ids.append(int(ident))
                continue

            ident = str(ident).strip()
            if not ident:
                continue

            row = conn.execute("SELECT id FROM genres WHERE genre_name LIKE ?", (ident,)).fetchone()
            if row:
                ids.append(row["id"])
                continue

            cursor = conn.cursor()
            cursor.execute("INSERT INTO genres (genre_name) VALUES (?)", (ident,))
            ids.append(cursor.lastrowid)
        return ids

    def import_song(self, file_path, song_data):
        """Copies an audio file into 'song/' and registers its metadata and relations."""
        if not self.db_path:
            return {"status": "error", "message": "Library not initialized"}
        if not os.path.exists(file_path):
            return {"status": "error", "message": "Source file not found"}

        conn = database.get_db_connection(self.db_path)
        dest_path = None
        try:
            song_name = song_data.get("song_name", "").strip()
            if not song_name:
                song_name = os.path.splitext(os.path.basename(file_path))[0]

            ext = os.path.splitext(file_path)[1].lower()
            song_dir = os.path.join(self.library_path, "song")
            unique_filename = generate_unique_slug(song_name, song_dir, extension=ext) + ext
            dest_path = os.path.join(song_dir, unique_filename)

            shutil.copy2(file_path, dest_path)
            duration = self.get_audio_duration(dest_path)

            key_id = None
            if song_data.get("key"):
                row = conn.execute("SELECT id FROM keys WHERE key_name = ?", (song_data["key"],)).fetchone()
                if row:
                    key_id = row["id"]

            scale_id = None
            if song_data.get("scale"):
                row = conn.execute("SELECT id FROM scales WHERE scale_name = ?", (song_data["scale"],)).fetchone()
                if row:
                    scale_id = row["id"]

            tempo = song_data.get("tempo")
            if tempo:
                try:
                    tempo = int(tempo)
                except ValueError:
                    tempo = None

            main_artists = self.resolve_artist_slugs(conn, song_data.get("main_artists", []))
            featured_artists = self.resolve_artist_slugs(conn, song_data.get("featured_artists", []))
            album_slug = self.resolve_album_slug(conn, song_data.get("album_slug"), main_artists)
            genres = self.resolve_genre_ids(conn, song_data.get("genres", []))

            conn.execute(
                "INSERT INTO songs (song_file, song_name, release_date, tempo, key_id, scale_id, duration) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (unique_filename, song_name, song_data.get("release_date"), tempo, key_id, scale_id, duration),
            )

            for artist_slug in main_artists:
                conn.execute(
                    "INSERT OR IGNORE INTO song_artists (song_file, artist_slug, is_featured) VALUES (?, ?, 0)",
                    (unique_filename, artist_slug),
                )

            for artist_slug in featured_artists:
                conn.execute(
                    "INSERT OR IGNORE INTO song_artists (song_file, artist_slug, is_featured) VALUES (?, ?, 1)",
                    (unique_filename, artist_slug),
                )

            for genre_id in genres:
                conn.execute(
                    "INSERT OR IGNORE INTO song_genres (song_file, genre_id) VALUES (?, ?)",
                    (unique_filename, genre_id),
                )

            track_num = song_data.get("track_number")
            if album_slug:
                if not track_num:
                    row = conn.execute(
                        "SELECT MAX(track_number) as max_t FROM album_songs WHERE album_slug = ?",
                        (album_slug,),
                    ).fetchone()
                    track_num = (row["max_t"] or 0) + 1
                conn.execute(
                    "INSERT INTO album_songs (album_slug, song_file, track_number) VALUES (?, ?, ?)",
                    (album_slug, unique_filename, int(track_num)),
                )

            conn.commit()
            return {"status": "success", "song_file": unique_filename, "song_name": song_name}
        except Exception as e:
            if dest_path and os.path.exists(dest_path):
                os.remove(dest_path)
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()

    def update_artist(self, slug, artist_data):
        """Updates artist details and re-saves aliases."""
        if not self.db_path:
            return {"status": "error", "message": "Library not initialized"}

        name = artist_data.get("name", "").strip()
        real_name = artist_data.get("real_name", "").strip() or name
        dob = artist_data.get("dob", "").strip()
        country_id = artist_data.get("country_id")

        if not name:
            return {"status": "error", "message": "Artist name is required"}

        conn = database.get_db_connection(self.db_path)
        try:
            artist_dir = os.path.join(self.library_path, "artist", slug)
            os.makedirs(artist_dir, exist_ok=True)

            avatar_path = None
            avatar_file_src = artist_data.get("avatar_file_src")
            if avatar_file_src and os.path.exists(avatar_file_src):
                ext = os.path.splitext(avatar_file_src)[1]
                avatar_filename = f"avatar{ext}"
                shutil.copy2(avatar_file_src, os.path.join(artist_dir, avatar_filename))
                avatar_path = f"artist/{slug}/{avatar_filename}"

            if avatar_path:
                conn.execute(
                    "UPDATE artists SET real_name = ?, date_of_birth = ?, country_id = ?, avatar_image = ? "
                    "WHERE slug = ?",
                    (real_name, dob, country_id, avatar_path, slug),
                )
            else:
                conn.execute(
                    "UPDATE artists SET real_name = ?, date_of_birth = ?, country_id = ? WHERE slug = ?",
                    (real_name, dob, country_id, slug),
                )

            conn.execute("DELETE FROM artist_names WHERE artist_slug = ?", (slug,))
            conn.execute("INSERT INTO artist_names (artist_slug, name) VALUES (?, ?)", (slug, name))

            for alias in artist_data.get("aliases", []):
                alias = alias.strip()
                if alias and alias != name:
                    conn.execute(
                        "INSERT OR IGNORE INTO artist_names (artist_slug, name) VALUES (?, ?)",
                        (slug, alias),
                    )

            conn.commit()
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()

    def update_album(self, slug, album_data):
        """Updates album details and optional cover artwork."""
        if not self.db_path:
            return {"status": "error", "message": "Library not initialized"}

        name = album_data.get("name", "").strip()
        release_date = album_data.get("release_date", "").strip()
        artist_slug = album_data.get("artist_slug")

        if not name:
            return {"status": "error", "message": "Album name is required"}

        conn = database.get_db_connection(self.db_path)
        try:
            album_dir = os.path.join(self.library_path, "album", slug)
            os.makedirs(album_dir, exist_ok=True)

            cover_path = None
            cover_file_src = album_data.get("cover_file_src")
            if cover_file_src and os.path.exists(cover_file_src):
                ext = os.path.splitext(cover_file_src)[1]
                cover_filename = f"cover{ext}"
                shutil.copy2(cover_file_src, os.path.join(album_dir, cover_filename))
                cover_path = f"album/{slug}/{cover_filename}"

            if cover_path:
                conn.execute(
                    "UPDATE albums SET album_name = ?, release_date = ?, album_cover = ?, artist_slug = ? "
                    "WHERE slug = ?",
                    (name, release_date, cover_path, artist_slug, slug),
                )
            else:
                conn.execute(
                    "UPDATE albums SET album_name = ?, release_date = ?, artist_slug = ? WHERE slug = ?",
                    (name, release_date, artist_slug, slug),
                )
            conn.commit()
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()

    def update_song(self, song_file, song_data):
        """Updates existing song metadata and relations."""
        if not self.db_path:
            return {"status": "error", "message": "Library not initialized"}

        conn = database.get_db_connection(self.db_path)
        try:
            song_name = song_data.get("song_name", "").strip()
            if not song_name:
                return {"status": "error", "message": "Song name is required"}

            key_id = None
            if song_data.get("key"):
                row = conn.execute("SELECT id FROM keys WHERE key_name = ?", (song_data["key"],)).fetchone()
                if row:
                    key_id = row["id"]

            scale_id = None
            if song_data.get("scale"):
                row = conn.execute("SELECT id FROM scales WHERE scale_name = ?", (song_data["scale"],)).fetchone()
                if row:
                    scale_id = row["id"]

            tempo = song_data.get("tempo")
            if tempo:
                try:
                    tempo = int(tempo)
                except ValueError:
                    tempo = None

            main_artists = self.resolve_artist_slugs(conn, song_data.get("main_artists", []))
            featured_artists = self.resolve_artist_slugs(conn, song_data.get("featured_artists", []))
            album_slug = self.resolve_album_slug(conn, song_data.get("album_slug"), main_artists)
            genres = self.resolve_genre_ids(conn, song_data.get("genres", []))

            conn.execute(
                "UPDATE songs SET song_name = ?, release_date = ?, tempo = ?, key_id = ?, scale_id = ? "
                "WHERE song_file = ?",
                (song_name, song_data.get("release_date"), tempo, key_id, scale_id, song_file),
            )

            conn.execute("DELETE FROM song_artists WHERE song_file = ?", (song_file,))
            for artist_slug in main_artists:
                conn.execute(
                    "INSERT OR IGNORE INTO song_artists (song_file, artist_slug, is_featured) VALUES (?, ?, 0)",
                    (song_file, artist_slug),
                )

            for artist_slug in featured_artists:
                conn.execute(
                    "INSERT OR IGNORE INTO song_artists (song_file, artist_slug, is_featured) VALUES (?, ?, 1)",
                    (song_file, artist_slug),
                )

            conn.execute("DELETE FROM song_genres WHERE song_file = ?", (song_file,))
            for genre_id in genres:
                conn.execute(
                    "INSERT OR IGNORE INTO song_genres (song_file, genre_id) VALUES (?, ?)",
                    (song_file, genre_id),
                )

            conn.execute("DELETE FROM album_songs WHERE song_file = ?", (song_file,))
            track_num = song_data.get("track_number")
            if album_slug:
                if not track_num:
                    row = conn.execute(
                        "SELECT MAX(track_number) as max_t FROM album_songs WHERE album_slug = ?",
                        (album_slug,),
                    ).fetchone()
                    track_num = (row["max_t"] or 0) + 1
                conn.execute(
                    "INSERT INTO album_songs (album_slug, song_file, track_number) VALUES (?, ?, ?)",
                    (album_slug, song_file, int(track_num)),
                )

            conn.commit()
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()

    def get_songs(self, filters=None):
        """Fetches all songs with joined artist, album, genre, key, and scale metadata."""
        if not self.db_path:
            return []
        conn = database.get_db_connection(self.db_path)
        try:
            query = """
                SELECT s.song_file, s.song_name, s.release_date, s.tempo, s.duration,
                       k.key_name, sc.scale_name,
                       (SELECT GROUP_CONCAT(a.real_name, ', ')
                        FROM song_artists sa
                        JOIN artists a ON sa.artist_slug = a.slug
                        WHERE sa.song_file = s.song_file AND sa.is_featured = 0) as main_artists,
                       (SELECT GROUP_CONCAT(sa.artist_slug, ', ')
                        FROM song_artists sa
                        WHERE sa.song_file = s.song_file AND sa.is_featured = 0) as main_artists_slugs,
                       (SELECT GROUP_CONCAT(a.real_name, ', ')
                        FROM song_artists sa
                        JOIN artists a ON sa.artist_slug = a.slug
                        WHERE sa.song_file = s.song_file AND sa.is_featured = 1) as feat_artists,
                       (SELECT GROUP_CONCAT(sa.artist_slug, ', ')
                        FROM song_artists sa
                        WHERE sa.song_file = s.song_file AND sa.is_featured = 1) as feat_artists_slugs,
                       (SELECT GROUP_CONCAT(g.genre_name, ', ')
                        FROM song_genres sg
                        JOIN genres g ON sg.genre_id = g.id
                        WHERE sg.song_file = s.song_file) as genres,
                       (SELECT GROUP_CONCAT(sg.genre_id, ', ')
                        FROM song_genres sg
                        WHERE sg.song_file = s.song_file) as genres_ids,
                       al.album_name, al.slug as album_slug, als.track_number
                FROM songs s
                LEFT JOIN keys k ON s.key_id = k.id
                LEFT JOIN scales sc ON s.scale_id = sc.id
                LEFT JOIN album_songs als ON s.song_file = als.song_file
                LEFT JOIN albums al ON als.album_slug = al.slug
            """
            rows = conn.execute(query).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_stats(self):
        """Gets overview counts for the dashboard."""
        if not self.db_path:
            return {"songs": 0, "artists": 0, "albums": 0, "genres": 0}
        conn = database.get_db_connection(self.db_path)
        try:
            return {
                "songs": conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0],
                "artists": conn.execute("SELECT COUNT(*) FROM artists").fetchone()[0],
                "albums": conn.execute("SELECT COUNT(*) FROM albums").fetchone()[0],
                "genres": conn.execute("SELECT COUNT(*) FROM genres").fetchone()[0],
            }
        finally:
            conn.close()
