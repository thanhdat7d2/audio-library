"""Song registration, audio attachment, updates, and catalog listing."""

import os
import shutil

from .. import database
from ..slug_engine import generate_unique_slug
from .projects import ensure_project_link
from .resolvers import (
    generate_unique_song_key,
    get_audio_duration,
    resolve_album_slug,
    resolve_artist_slugs,
    resolve_genre_ids,
    resolve_tag_ids,
)


def _lookup_key_scale_tempo(conn, song_data: dict):
    key_id = None
    if song_data.get("key"):
        row = conn.execute(
            "SELECT id FROM keys WHERE LOWER(key_name) = LOWER(?)",
            (str(song_data["key"]).strip(),),
        ).fetchone()
        if row:
            key_id = row["id"]

    scale_id = None
    if song_data.get("scale"):
        row = conn.execute(
            "SELECT id FROM scales WHERE LOWER(scale_name) = LOWER(?)",
            (str(song_data["scale"]).strip(),),
        ).fetchone()
        if row:
            scale_id = row["id"]

    tempo = song_data.get("tempo")
    if tempo not in (None, ""):
        try:
            tempo = int(float(tempo))
        except (TypeError, ValueError):
            tempo = None
    else:
        tempo = None

    return key_id, scale_id, tempo


def _collect_tags(song_data: dict) -> list:
    raw_tags = list(song_data.get("tags", []))
    if song_data.get("ai_generated") and not any(
        str(t).strip().lower() == "ai generated" for t in raw_tags
    ):
        raw_tags.append("AI Generated")
    return raw_tags


def _sync_song_relations(conn, library_path: str, song_file: str, song_data: dict, replace_existing: bool = False):
    main_artists = resolve_artist_slugs(conn, library_path, song_data.get("main_artists", []))
    featured_artists = resolve_artist_slugs(conn, library_path, song_data.get("featured_artists", []))
    album_slug = resolve_album_slug(conn, library_path, song_data.get("album_slug"), main_artists)
    genres = resolve_genre_ids(conn, song_data.get("genres", []))

    if replace_existing:
        conn.execute("DELETE FROM song_artists WHERE song_file = ?", (song_file,))
        conn.execute("DELETE FROM song_genres WHERE song_file = ?", (song_file,))
        conn.execute("DELETE FROM album_songs WHERE song_file = ?", (song_file,))

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
    for genre_id in genres:
        conn.execute(
            "INSERT OR IGNORE INTO song_genres (song_file, genre_id) VALUES (?, ?)",
            (song_file, genre_id),
        )

    if not replace_existing or "tags" in song_data or "ai_generated" in song_data:
        tags = resolve_tag_ids(conn, _collect_tags(song_data))
        if replace_existing:
            conn.execute("DELETE FROM song_tags WHERE song_file = ?", (song_file,))
        for tag_id in tags:
            conn.execute(
                "INSERT OR IGNORE INTO song_tags (song_file, tag_id) VALUES (?, ?)",
                (song_file, tag_id),
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
            (album_slug, song_file, int(track_num)),
        )

    if song_data.get("project_path"):
        ensure_project_link(conn, "song", song_file, song_data.get("project_path"), song_data.get("project_name"))


def import_song(db_path: str, library_path: str, file_path, song_data: dict, move_file: bool = False) -> dict:
    """Registers a song (copying or moving audio into 'song/' when file_path is provided, or metadata-only if omitted)."""
    song_data = song_data or {}
    has_file = bool(file_path and str(file_path).strip())
    if has_file and not os.path.exists(file_path):
        return {"status": "error", "message": "Source file not found"}

    conn = database.get_db_connection(db_path)
    dest_path = None
    moved = False
    try:
        song_name = str(song_data.get("song_name") or "").strip()
        if not song_name:
            if has_file:
                song_name = os.path.splitext(os.path.basename(file_path))[0]
            else:
                return {"status": "error", "message": "Song name is required when no audio file is provided"}

        song_dir = os.path.join(library_path, "song")
        os.makedirs(song_dir, exist_ok=True)

        if has_file:
            ext = os.path.splitext(file_path)[1].lower()
            unique_filename = generate_unique_song_key(conn, library_path, song_name, extension=ext)
            dest_path = os.path.join(song_dir, unique_filename)
            if move_file:
                shutil.move(file_path, dest_path)
                moved = True
            else:
                shutil.copy2(file_path, dest_path)
            duration = get_audio_duration(dest_path)
            has_audio = 1
            audio_file = unique_filename
        else:
            unique_filename = generate_unique_song_key(conn, library_path, song_name, extension="")
            try:
                duration = float(song_data.get("duration") or 0.0)
            except (TypeError, ValueError):
                duration = 0.0
            has_audio = 0
            audio_file = None

        key_id, scale_id, tempo = _lookup_key_scale_tempo(conn, song_data)

        conn.execute(
            "INSERT INTO songs (song_file, song_name, release_date, tempo, key_id, scale_id, duration, has_audio, audio_file) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                unique_filename,
                song_name,
                song_data.get("release_date") or None,
                tempo,
                key_id,
                scale_id,
                duration,
                has_audio,
                audio_file,
            ),
        )

        _sync_song_relations(conn, library_path, unique_filename, song_data, replace_existing=False)
        conn.commit()
        return {
            "status": "success",
            "song_file": unique_filename,
            "audio_file": audio_file,
            "has_audio": bool(has_audio),
            "song_name": song_name,
        }
    except Exception as e:
        if dest_path and os.path.exists(dest_path):
            if moved:
                shutil.move(dest_path, file_path)
            else:
                os.remove(dest_path)
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def attach_song_audio(db_path: str, library_path: str, song_file: str, file_path: str) -> dict:
    """Attaches or replaces the physical audio file for an existing song entry."""
    if not file_path or not os.path.exists(file_path):
        return {"status": "error", "message": "Source audio file not found"}

    conn = database.get_db_connection(db_path)
    dest_path = None
    try:
        row = conn.execute(
            "SELECT song_file, song_name, has_audio, audio_file FROM songs WHERE song_file = ?",
            (song_file,),
        ).fetchone()
        if not row:
            return {"status": "error", "message": "Song not found"}

        ext = os.path.splitext(file_path)[1].lower()
        song_dir = os.path.join(library_path, "song")
        os.makedirs(song_dir, exist_ok=True)

        unique_audio = generate_unique_slug(row["song_name"], song_dir, extension=ext) + ext
        dest_path = os.path.join(song_dir, unique_audio)
        shutil.copy2(file_path, dest_path)
        duration = get_audio_duration(dest_path)

        old_audio = row["audio_file"]
        conn.execute(
            "UPDATE songs SET audio_file = ?, has_audio = 1, duration = ? WHERE song_file = ?",
            (unique_audio, duration, song_file),
        )
        conn.commit()

        if old_audio and old_audio != unique_audio:
            old_path = os.path.join(song_dir, old_audio)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass

        return {
            "status": "success",
            "song_file": song_file,
            "audio_file": unique_audio,
            "duration": duration,
        }
    except Exception as e:
        if dest_path and os.path.exists(dest_path):
            os.remove(dest_path)
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def update_song(db_path: str, library_path: str, song_file: str, song_data: dict) -> dict:
    """Updates existing song metadata, tags, relations, and optional project link."""
    song_name = song_data.get("song_name", "").strip()
    if not song_name:
        return {"status": "error", "message": "Song name is required"}

    conn = database.get_db_connection(db_path)
    try:
        key_id, scale_id, tempo = _lookup_key_scale_tempo(conn, song_data)
        conn.execute(
            "UPDATE songs SET song_name = ?, release_date = ?, tempo = ?, key_id = ?, scale_id = ? "
            "WHERE song_file = ?",
            (song_name, song_data.get("release_date") or None, tempo, key_id, scale_id, song_file),
        )
        _sync_song_relations(conn, library_path, song_file, song_data, replace_existing=True)
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def get_songs(db_path: str) -> list[dict]:
    """Fetches all songs with joined artist, album, genre, tag, key, scale, audio, and project metadata."""
    conn = database.get_db_connection(db_path)
    try:
        query = """
            SELECT s.song_file, s.song_name, s.release_date, s.tempo, s.duration,
                   s.has_audio,
                   COALESCE(s.audio_file, CASE WHEN s.has_audio = 1 THEN s.song_file ELSE NULL END) as audio_file,
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
                   (SELECT GROUP_CONCAT(t.tag_name, ', ')
                    FROM song_tags st
                    JOIN tags t ON st.tag_id = t.id
                    WHERE st.song_file = s.song_file) as tags,
                   (SELECT GROUP_CONCAT(st.tag_id, ', ')
                    FROM song_tags st
                    WHERE st.song_file = s.song_file) as tags_ids,
                   (SELECT COUNT(*)
                    FROM projects p
                    WHERE p.entity_type = 'song' AND p.entity_id = s.song_file) as project_count,
                   al.album_name, al.slug as album_slug, al.album_cover, als.track_number
            FROM songs s
            LEFT JOIN keys k ON s.key_id = k.id
            LEFT JOIN scales sc ON s.scale_id = sc.id
            LEFT JOIN album_songs als ON s.song_file = als.song_file
            LEFT JOIN albums al ON als.album_slug = al.slug
        """
        return [dict(row) for row in conn.execute(query).fetchall()]
    finally:
        conn.close()
