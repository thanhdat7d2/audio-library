import os
import sqlite3

from .db_schema import (
    SCHEMA_STATEMENTS,
    SEED_COUNTRIES,
    SEED_GENRES,
    SEED_KEYS,
    SEED_SCALES,
    SEED_TAGS,
)


def get_db_connection(db_path: str) -> sqlite3.Connection:
    """Establishes a connection to the SQLite database with foreign keys enabled."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _migrate_songs_table(cursor: sqlite3.Cursor) -> None:
    """Applies additive migrations for existing songs tables."""
    song_columns = {
        row["name"]
        for row in cursor.execute("PRAGMA table_info(songs);").fetchall()
    }
    if "has_audio" not in song_columns:
        cursor.execute("ALTER TABLE songs ADD COLUMN has_audio INTEGER NOT NULL DEFAULT 1;")
    if "audio_file" not in song_columns:
        cursor.execute("ALTER TABLE songs ADD COLUMN audio_file TEXT;")
    cursor.execute(
        "UPDATE songs SET audio_file = song_file WHERE has_audio = 1 AND (audio_file IS NULL OR audio_file = '');"
    )


def _seed_reference_data(cursor: sqlite3.Cursor) -> None:
    """Populates default musical keys, scales, countries, genres, and tags."""
    for key in SEED_KEYS:
        cursor.execute("INSERT OR IGNORE INTO keys (key_name) VALUES (?);", (key,))
    for scale in SEED_SCALES:
        cursor.execute("INSERT OR IGNORE INTO scales (scale_name) VALUES (?);", (scale,))
    for country in SEED_COUNTRIES:
        cursor.execute("INSERT OR IGNORE INTO countries (country_name) VALUES (?);", (country,))
    for genre in SEED_GENRES:
        cursor.execute("INSERT OR IGNORE INTO genres (genre_name) VALUES (?);", (genre,))
    for tag in SEED_TAGS:
        cursor.execute("INSERT OR IGNORE INTO tags (tag_name) VALUES (?);", (tag,))


def init_db(db_path: str) -> None:
    """Initializes the SQLite database schema, migrations, and default seed data."""
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        for statement in SCHEMA_STATEMENTS:
            cursor.execute(statement)

        _migrate_songs_table(cursor)
        _seed_reference_data(cursor)
        conn.commit()
    finally:
        conn.close()


def get_config(db_path: str, key: str):
    """Fetches a configuration value by key from the library database."""
    conn = get_db_connection(db_path)
    try:
        res = conn.execute("SELECT value FROM config WHERE key = ?;", (key,)).fetchone()
        return res["value"] if res else None
    finally:
        conn.close()


def set_config(db_path: str, key: str, value: str) -> None:
    """Stores or updates a configuration value in the library database."""
    conn = get_db_connection(db_path)
    try:
        conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?);", (key, value))
        conn.commit()
    finally:
        conn.close()
