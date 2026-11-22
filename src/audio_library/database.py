import os
import sqlite3


def get_db_connection(db_path: str) -> sqlite3.Connection:
    """Establishes a connection to the SQLite database with foreign keys enabled."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str) -> None:
    """Initializes the SQLite database schema and default seed data."""
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Countries Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS countries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_name TEXT UNIQUE NOT NULL
    );
    """)

    # 2. Artists Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS artists (
        slug TEXT PRIMARY KEY,
        real_name TEXT,
        date_of_birth TEXT,
        country_id INTEGER REFERENCES countries(id) ON DELETE SET NULL,
        avatar_image TEXT
    );
    """)

    # 3. Artist Names (multiple names/aliases for artists)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS artist_names (
        artist_slug TEXT REFERENCES artists(slug) ON DELETE CASCADE,
        name TEXT,
        PRIMARY KEY (artist_slug, name)
    );
    """)

    # 4. Genres Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS genres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        genre_name TEXT UNIQUE NOT NULL,
        sub_genre_of INTEGER REFERENCES genres(id) ON DELETE SET NULL
    );
    """)

    # 5. Moods Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS moods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mood_name TEXT UNIQUE NOT NULL
    );
    """)

    # 6. Keys Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_name TEXT UNIQUE NOT NULL
    );
    """)

    # 7. Scales Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scale_name TEXT UNIQUE NOT NULL
    );
    """)

    # 8. Songs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS songs (
        song_file TEXT PRIMARY KEY,
        song_name TEXT NOT NULL,
        release_date TEXT,
        tempo INTEGER,
        key_id INTEGER REFERENCES keys(id) ON DELETE SET NULL,
        scale_id INTEGER REFERENCES scales(id) ON DELETE SET NULL,
        duration REAL
    );
    """)

    # 9. Song-Artist link
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS song_artists (
        song_file TEXT REFERENCES songs(song_file) ON DELETE CASCADE,
        artist_slug TEXT REFERENCES artists(slug) ON DELETE CASCADE,
        is_featured INTEGER DEFAULT 0, -- 0 = Main, 1 = Featured
        PRIMARY KEY (song_file, artist_slug)
    );
    """)

    # 10. Song-Genre link
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS song_genres (
        song_file TEXT REFERENCES songs(song_file) ON DELETE CASCADE,
        genre_id INTEGER REFERENCES genres(id) ON DELETE CASCADE,
        PRIMARY KEY (song_file, genre_id)
    );
    """)

    # 11. Albums Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS albums (
        slug TEXT PRIMARY KEY,
        album_name TEXT NOT NULL,
        release_date TEXT,
        album_cover TEXT,
        artist_slug TEXT REFERENCES artists(slug) ON DELETE SET NULL
    );
    """)

    # 12. Album Songs link
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS album_songs (
        album_slug TEXT REFERENCES albums(slug) ON DELETE CASCADE,
        song_file TEXT REFERENCES songs(song_file) ON DELETE CASCADE,
        track_number INTEGER NOT NULL,
        PRIMARY KEY (album_slug, song_file)
    );
    """)

    # 13. Mixtapes Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mixtapes (
        slug TEXT PRIMARY KEY,
        mixtape_name TEXT NOT NULL,
        description TEXT
    );
    """)

    # 14. Mixtape Songs link
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mixtape_songs (
        mixtape_slug TEXT REFERENCES mixtapes(slug) ON DELETE CASCADE,
        song_file TEXT REFERENCES songs(song_file) ON DELETE CASCADE,
        track_number INTEGER NOT NULL,
        PRIMARY KEY (mixtape_slug, song_file)
    );
    """)

    # 15. Mixtape Genres link
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mixtape_genres (
        mixtape_slug TEXT REFERENCES mixtapes(slug) ON DELETE CASCADE,
        genre_id INTEGER REFERENCES genres(id) ON DELETE CASCADE,
        PRIMARY KEY (mixtape_slug, genre_id)
    );
    """)

    # 16. Playlists Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS playlists (
        slug TEXT PRIMARY KEY,
        playlist_name TEXT NOT NULL,
        description TEXT
    );
    """)

    # 17. Playlist Songs link
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS playlist_songs (
        playlist_slug TEXT REFERENCES playlists(slug) ON DELETE CASCADE,
        song_file TEXT REFERENCES songs(song_file) ON DELETE CASCADE,
        track_number INTEGER NOT NULL,
        PRIMARY KEY (playlist_slug, song_file)
    );
    """)

    # 18. Playlist Genres link
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS playlist_genres (
        playlist_slug TEXT REFERENCES playlists(slug) ON DELETE CASCADE,
        genre_id INTEGER REFERENCES genres(id) ON DELETE CASCADE,
        PRIMARY KEY (playlist_slug, genre_id)
    );
    """)

    # 19. Playlist Moods link
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS playlist_moods (
        playlist_slug TEXT REFERENCES playlists(slug) ON DELETE CASCADE,
        mood_id INTEGER REFERENCES moods(id) ON DELETE CASCADE,
        PRIMARY KEY (playlist_slug, mood_id)
    );
    """)

    # 20. Sample Packs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sample_packs (
        slug TEXT PRIMARY KEY,
        pack_name TEXT NOT NULL,
        description TEXT
    );
    """)

    # 21. Samples Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS samples (
        file_path TEXT PRIMARY KEY, -- relative to samplepack/pack_slug/
        sample_pack_slug TEXT REFERENCES sample_packs(slug) ON DELETE CASCADE,
        sample_name TEXT NOT NULL,
        genre_id INTEGER REFERENCES genres(id) ON DELETE SET NULL,
        tempo INTEGER,
        key_id INTEGER REFERENCES keys(id) ON DELETE SET NULL,
        scale_id INTEGER REFERENCES scales(id) ON DELETE SET NULL
    );
    """)

    # 22. Loop Packs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS loop_packs (
        slug TEXT PRIMARY KEY,
        pack_name TEXT NOT NULL,
        description TEXT
    );
    """)

    # 23. Loops Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS loops (
        file_path TEXT PRIMARY KEY, -- relative to looppack/pack_slug/
        loop_pack_slug TEXT REFERENCES loop_packs(slug) ON DELETE CASCADE,
        loop_name TEXT NOT NULL,
        genre_id INTEGER REFERENCES genres(id) ON DELETE SET NULL,
        tempo INTEGER,
        key_id INTEGER REFERENCES keys(id) ON DELETE SET NULL,
        scale_id INTEGER REFERENCES scales(id) ON DELETE SET NULL
    );
    """)

    # 24. Stems Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stems (
        slug TEXT PRIMARY KEY,
        stem_name TEXT NOT NULL,
        song_file TEXT REFERENCES songs(song_file) ON DELETE SET NULL
    );
    """)

    # 25. Stem Files
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stem_files (
        file_path TEXT PRIMARY KEY, -- relative to stem/stem_slug/
        stem_slug TEXT REFERENCES stems(slug) ON DELETE CASCADE,
        track_name TEXT NOT NULL
    );
    """)

    # 26. Configuration Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)

    # Seed reference data
    seed_keys = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    for key in seed_keys:
        cursor.execute("INSERT OR IGNORE INTO keys (key_name) VALUES (?);", (key,))

    seed_scales = [
        "Major", "Minor", "Pentatonic", "Blues Scale", "Harmonic Minor",
        "Melodic Minor", "Dorian", "Phrygian", "Lydian", "Mixolydian",
        "Aeolian", "Locrian",
    ]
    for scale in seed_scales:
        cursor.execute("INSERT OR IGNORE INTO scales (scale_name) VALUES (?);", (scale,))

    seed_countries = [
        "Vietnam", "United States", "United Kingdom", "Japan", "Germany",
        "France", "Russia", "South Korea", "Sweden", "Canada",
    ]
    for country in seed_countries:
        cursor.execute("INSERT OR IGNORE INTO countries (country_name) VALUES (?);", (country,))

    seed_genres = [
        "Classical", "Lo-Fi", "Electronic", "Ambient", "Synthwave",
        "Hip Hop", "Rock", "Pop", "Jazz", "Cinematic", "Folk", "Sound Effects",
    ]
    for genre in seed_genres:
        cursor.execute("INSERT OR IGNORE INTO genres (genre_name) VALUES (?);", (genre,))

    conn.commit()
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
