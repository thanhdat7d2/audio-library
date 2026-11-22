"""Artist, album, genre, mood, tag CRUD and library overview queries."""

import os
import shutil

from .. import database
from ..slug_engine import generate_unique_slug
from .projects import ensure_project_link


def get_metadata_options(db_path: str) -> dict:
    """Fetches reference metadata lists (keys, scales, genres, moods, tags, artists, albums, countries)."""
    conn = database.get_db_connection(db_path)
    try:
        return {
            "keys": [row["key_name"] for row in conn.execute("SELECT key_name FROM keys").fetchall()],
            "scales": [row["scale_name"] for row in conn.execute("SELECT scale_name FROM scales").fetchall()],
            "genres": [dict(r) for r in conn.execute("SELECT id, genre_name FROM genres ORDER BY genre_name").fetchall()],
            "moods": [dict(r) for r in conn.execute("SELECT id, mood_name FROM moods ORDER BY mood_name").fetchall()],
            "tags": [dict(r) for r in conn.execute("SELECT id, tag_name FROM tags ORDER BY tag_name").fetchall()],
            "artists": [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT a.slug, a.real_name, a.date_of_birth, a.country_id, a.avatar_image,
                           (SELECT COUNT(*) FROM projects p
                            WHERE p.entity_type = 'artist' AND p.entity_id = a.slug) as project_count
                    FROM artists a
                    ORDER BY a.real_name
                    """
                ).fetchall()
            ],
            "albums": [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT al.slug, al.album_name, al.release_date, al.album_cover, al.artist_slug,
                           (SELECT COUNT(*) FROM projects p
                            WHERE p.entity_type = 'album' AND p.entity_id = al.slug) as project_count
                    FROM albums al
                    ORDER BY al.album_name
                    """
                ).fetchall()
            ],
            "countries": [dict(r) for r in conn.execute("SELECT id, country_name FROM countries ORDER BY country_name").fetchall()],
        }
    finally:
        conn.close()


def get_stats(db_path: str) -> dict:
    """Gets overview counts for the dashboard."""
    conn = database.get_db_connection(db_path)
    try:
        return {
            "songs": conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0],
            "artists": conn.execute("SELECT COUNT(*) FROM artists").fetchone()[0],
            "albums": conn.execute("SELECT COUNT(*) FROM albums").fetchone()[0],
            "genres": conn.execute("SELECT COUNT(*) FROM genres").fetchone()[0],
            "tags": conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0],
            "projects": conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0],
            "songs_without_audio": conn.execute("SELECT COUNT(*) FROM songs WHERE has_audio = 0").fetchone()[0],
        }
    finally:
        conn.close()


def create_artist(db_path: str, library_path: str, artist_data: dict) -> dict:
    name = artist_data.get("name", "").strip()
    real_name = artist_data.get("real_name", "").strip() or name
    dob = artist_data.get("dob", "").strip()
    country_id = artist_data.get("country_id")

    if not name:
        return {"status": "error", "message": "Artist name is required"}

    conn = database.get_db_connection(db_path)
    try:
        slug = generate_unique_slug(name, os.path.join(library_path, "artist"))
        artist_dir = os.path.join(library_path, "artist", slug)
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
        conn.execute("INSERT INTO artist_names (artist_slug, name) VALUES (?, ?)", (slug, name))

        for alias in artist_data.get("aliases", []):
            alias = alias.strip()
            if alias and alias != name:
                conn.execute(
                    "INSERT OR IGNORE INTO artist_names (artist_slug, name) VALUES (?, ?)",
                    (slug, alias),
                )

        if artist_data.get("project_path"):
            ensure_project_link(conn, "artist", slug, artist_data.get("project_path"), artist_data.get("project_name"))

        conn.commit()
        return {"status": "success", "slug": slug, "name": name}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def update_artist(db_path: str, library_path: str, slug: str, artist_data: dict) -> dict:
    name = artist_data.get("name", "").strip()
    real_name = artist_data.get("real_name", "").strip() or name
    dob = artist_data.get("dob", "").strip()
    country_id = artist_data.get("country_id")

    if not name:
        return {"status": "error", "message": "Artist name is required"}

    conn = database.get_db_connection(db_path)
    try:
        artist_dir = os.path.join(library_path, "artist", slug)
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
                "UPDATE artists SET real_name = ?, date_of_birth = ?, country_id = ?, avatar_image = ? WHERE slug = ?",
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

        if artist_data.get("project_path"):
            ensure_project_link(conn, "artist", slug, artist_data.get("project_path"), artist_data.get("project_name"))

        conn.commit()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def create_album(db_path: str, library_path: str, album_data: dict) -> dict:
    name = album_data.get("name", "").strip()
    release_date = album_data.get("release_date", "").strip()
    artist_slug = album_data.get("artist_slug")

    if not name:
        return {"status": "error", "message": "Album name is required"}

    conn = database.get_db_connection(db_path)
    try:
        slug = generate_unique_slug(name, os.path.join(library_path, "album"))
        album_dir = os.path.join(library_path, "album", slug)
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

        if album_data.get("project_path"):
            ensure_project_link(conn, "album", slug, album_data.get("project_path"), album_data.get("project_name"))

        conn.commit()
        return {"status": "success", "slug": slug, "name": name}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def update_album(db_path: str, library_path: str, slug: str, album_data: dict) -> dict:
    name = album_data.get("name", "").strip()
    release_date = album_data.get("release_date", "").strip()
    artist_slug = album_data.get("artist_slug")

    if not name:
        return {"status": "error", "message": "Album name is required"}

    conn = database.get_db_connection(db_path)
    try:
        album_dir = os.path.join(library_path, "album", slug)
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
                "UPDATE albums SET album_name = ?, release_date = ?, album_cover = ?, artist_slug = ? WHERE slug = ?",
                (name, release_date, cover_path, artist_slug, slug),
            )
        else:
            conn.execute(
                "UPDATE albums SET album_name = ?, release_date = ?, artist_slug = ? WHERE slug = ?",
                (name, release_date, artist_slug, slug),
            )

        if album_data.get("project_path"):
            ensure_project_link(conn, "album", slug, album_data.get("project_path"), album_data.get("project_name"))

        conn.commit()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def create_genre(db_path: str, name: str, parent_id=None) -> dict:
    conn = database.get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO genres (genre_name, sub_genre_of) VALUES (?, ?)", (name.strip(), parent_id))
        conn.commit()
        return {"status": "success", "id": cursor.lastrowid}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def create_mood(db_path: str, name: str) -> dict:
    conn = database.get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO moods (mood_name) VALUES (?)", (name.strip(),))
        conn.commit()
        return {"status": "success", "id": cursor.lastrowid}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def create_tag(db_path: str, name: str) -> dict:
    clean_name = str(name or "").strip()
    if not clean_name:
        return {"status": "error", "message": "Tag name is required"}
    conn = database.get_db_connection(db_path)
    try:
        existing = conn.execute(
            "SELECT id, tag_name FROM tags WHERE LOWER(tag_name) = LOWER(?)",
            (clean_name,),
        ).fetchone()
        if existing:
            return {"status": "success", "id": existing["id"], "tag_name": existing["tag_name"]}
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tags (tag_name) VALUES (?)", (clean_name,))
        conn.commit()
        return {"status": "success", "id": cursor.lastrowid, "tag_name": clean_name}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()
