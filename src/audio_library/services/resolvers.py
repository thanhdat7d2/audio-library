"""Entity resolution and audio metadata helpers."""

import os

from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE

from ..slug_engine import generate_unique_slug, slugify


def get_audio_duration(file_path: str) -> float:
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


def resolve_artist_slugs(conn, library_path: str, artist_identifiers) -> list[str]:
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

        new_slug = generate_unique_slug(ident, os.path.join(library_path, "artist"))
        os.makedirs(os.path.join(library_path, "artist", new_slug), exist_ok=True)
        conn.execute("INSERT INTO artists (slug, real_name) VALUES (?, ?)", (new_slug, ident))
        conn.execute("INSERT INTO artist_names (artist_slug, name) VALUES (?, ?)", (new_slug, ident))
        slugs.append(new_slug)
    return slugs


def resolve_album_slug(conn, library_path: str, album_identifier, main_artist_slugs=None) -> str | None:
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

    new_slug = generate_unique_slug(album_identifier, os.path.join(library_path, "album"))
    os.makedirs(os.path.join(library_path, "album", new_slug), exist_ok=True)
    artist_slug = main_artist_slugs[0] if main_artist_slugs else None
    conn.execute(
        "INSERT INTO albums (slug, album_name, artist_slug) VALUES (?, ?, ?)",
        (new_slug, album_identifier, artist_slug),
    )
    return new_slug


def resolve_genre_ids(conn, genre_identifiers) -> list[int]:
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

        row = conn.execute("SELECT id FROM genres WHERE LOWER(genre_name) = LOWER(?)", (ident,)).fetchone()
        if row:
            ids.append(row["id"])
            continue

        cursor = conn.cursor()
        cursor.execute("INSERT INTO genres (genre_name) VALUES (?)", (ident,))
        ids.append(cursor.lastrowid)
    return ids


def resolve_tag_ids(conn, tag_identifiers) -> list[int]:
    """Resolves tag IDs or names, auto-creating missing tags on the fly."""
    ids = []
    for ident in tag_identifiers:
        if not ident:
            continue
        if isinstance(ident, int) or (isinstance(ident, str) and ident.isdigit()):
            ids.append(int(ident))
            continue

        ident = str(ident).strip()
        if not ident:
            continue

        row = conn.execute("SELECT id FROM tags WHERE LOWER(tag_name) = LOWER(?)", (ident,)).fetchone()
        if row:
            ids.append(row["id"])
            continue

        cursor = conn.cursor()
        cursor.execute("INSERT INTO tags (tag_name) VALUES (?)", (ident,))
        ids.append(cursor.lastrowid)
    return ids


def generate_unique_song_key(conn, library_path: str, song_name: str, extension: str = "") -> str:
    """Generates a unique song_file key avoiding collisions in both song/ and the songs table."""
    slug = slugify(song_name)
    song_dir = os.path.join(library_path, "song")

    existing_keys = {
        row["song_file"].lower()
        for row in conn.execute("SELECT song_file FROM songs").fetchall()
    }
    if os.path.exists(song_dir):
        existing_keys.update(item.lower() for item in os.listdir(song_dir))

    candidate = f"{slug}{extension}"
    counter = 1
    while candidate.lower() in existing_keys:
        candidate = f"{slug}_{counter}{extension}"
        counter += 1
    return candidate
