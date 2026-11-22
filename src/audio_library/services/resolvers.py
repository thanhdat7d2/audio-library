"""Entity resolution and audio metadata helpers."""

import os
import re

import mutagen
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE

from ..slug_engine import generate_unique_slug, slugify


def extract_audio_metadata(file_path: str) -> dict:
    """Reads embedded audio tags (title, artist, album, genre, date, bpm, track, key) via mutagen."""
    meta = {
        "song_name": "",
        "main_artists": [],
        "album_slug": None,
        "genres": [],
        "release_date": None,
        "tempo": None,
        "track_number": None,
        "key": None,
        "scale": None,
    }
    try:
        audio = mutagen.File(file_path, easy=True)
        if not audio:
            return meta

        def first_val(keys):
            for k in keys:
                vals = audio.get(k)
                if vals:
                    text = str(vals[0]).strip()
                    if text:
                        return text
            return ""

        meta["song_name"] = first_val(("title",))
        artist_raw = first_val(("artist", "albumartist"))
        if artist_raw:
            parts = [p.strip() for p in re.split(r"[;]|(?:\s+(?:feat\.?|ft\.?|&|x)\s+)", artist_raw, flags=re.I) if p.strip()]
            meta["main_artists"] = parts[:5]

        meta["album_slug"] = first_val(("album",)) or None
        genre_raw = first_val(("genre",))
        if genre_raw:
            meta["genres"] = [g.strip() for g in re.split(r"[;,/]", genre_raw) if g.strip()][:5]

        date_raw = first_val(("date", "originaldate", "year"))
        if date_raw:
            meta["release_date"] = date_raw[:10]

        bpm_raw = first_val(("bpm", "tempo"))
        if bpm_raw:
            m = re.search(r"\d+(?:\.\d+)?", bpm_raw)
            if m:
                bpm_val = int(round(float(m.group(0))))
                if 20 <= bpm_val <= 300:
                    meta["tempo"] = bpm_val

        track_raw = first_val(("tracknumber",))
        if track_raw:
            m = re.match(r"(\d+)", track_raw)
            if m:
                meta["track_number"] = int(m.group(1))

        # Optional initial key (e.g. "Am", "C#m", "D Major", "F#")
        raw_audio = mutagen.File(file_path, easy=False)
        key_raw = ""
        if raw_audio and hasattr(raw_audio, "tags") and raw_audio.tags:
            for tag_key in ("TKEY", "initialkey", "INITIALKEY", "key"):
                if tag_key in raw_audio.tags:
                    val = raw_audio.tags[tag_key]
                    key_raw = str(val[0] if isinstance(val, list) else val).strip()
                    break
        if key_raw:
            km = re.match(r"^([A-Ga-g][#b]?)\s*(m|min|minor|maj|major)?$", key_raw, flags=re.I)
            if km:
                note = km.group(1).upper()
                flat_map = {"DB": "C#", "EB": "D#", "GB": "F#", "AB": "G#", "BB": "A#"}
                meta["key"] = flat_map.get(note, note)
                qual = (km.group(2) or "").lower()
                if qual in ("m", "min", "minor"):
                    meta["scale"] = "Minor"
                elif qual in ("maj", "major"):
                    meta["scale"] = "Major"
    except Exception:
        pass
    return meta


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
