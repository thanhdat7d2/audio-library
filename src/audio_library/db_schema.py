"""SQLite table definitions and default reference seed data."""

SCHEMA_STATEMENTS = (
    # 1. Countries
    """
    CREATE TABLE IF NOT EXISTS countries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_name TEXT UNIQUE NOT NULL
    );
    """,
    # 2. Artists
    """
    CREATE TABLE IF NOT EXISTS artists (
        slug TEXT PRIMARY KEY,
        real_name TEXT,
        date_of_birth TEXT,
        country_id INTEGER REFERENCES countries(id) ON DELETE SET NULL,
        avatar_image TEXT
    );
    """,
    # 3. Artist Names / Aliases
    """
    CREATE TABLE IF NOT EXISTS artist_names (
        artist_slug TEXT REFERENCES artists(slug) ON DELETE CASCADE,
        name TEXT,
        PRIMARY KEY (artist_slug, name)
    );
    """,
    # 4. Genres
    """
    CREATE TABLE IF NOT EXISTS genres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        genre_name TEXT UNIQUE NOT NULL,
        sub_genre_of INTEGER REFERENCES genres(id) ON DELETE SET NULL
    );
    """,
    # 5. Moods
    """
    CREATE TABLE IF NOT EXISTS moods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mood_name TEXT UNIQUE NOT NULL
    );
    """,
    # 6. Keys
    """
    CREATE TABLE IF NOT EXISTS keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_name TEXT UNIQUE NOT NULL
    );
    """,
    # 7. Scales
    """
    CREATE TABLE IF NOT EXISTS scales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scale_name TEXT UNIQUE NOT NULL
    );
    """,
    # 8. Songs
    """
    CREATE TABLE IF NOT EXISTS songs (
        song_file TEXT PRIMARY KEY,
        song_name TEXT NOT NULL,
        release_date TEXT,
        tempo INTEGER,
        key_id INTEGER REFERENCES keys(id) ON DELETE SET NULL,
        scale_id INTEGER REFERENCES scales(id) ON DELETE SET NULL,
        duration REAL,
        has_audio INTEGER NOT NULL DEFAULT 1,
        audio_file TEXT
    );
    """,
    # 9. Song-Artist link
    """
    CREATE TABLE IF NOT EXISTS song_artists (
        song_file TEXT REFERENCES songs(song_file) ON DELETE CASCADE,
        artist_slug TEXT REFERENCES artists(slug) ON DELETE CASCADE,
        is_featured INTEGER DEFAULT 0,
        PRIMARY KEY (song_file, artist_slug)
    );
    """,
    # 10. Song-Genre link
    """
    CREATE TABLE IF NOT EXISTS song_genres (
        song_file TEXT REFERENCES songs(song_file) ON DELETE CASCADE,
        genre_id INTEGER REFERENCES genres(id) ON DELETE CASCADE,
        PRIMARY KEY (song_file, genre_id)
    );
    """,
    # 11. Albums
    """
    CREATE TABLE IF NOT EXISTS albums (
        slug TEXT PRIMARY KEY,
        album_name TEXT NOT NULL,
        release_date TEXT,
        album_cover TEXT,
        artist_slug TEXT REFERENCES artists(slug) ON DELETE SET NULL
    );
    """,
    # 12. Album Songs link
    """
    CREATE TABLE IF NOT EXISTS album_songs (
        album_slug TEXT REFERENCES albums(slug) ON DELETE CASCADE,
        song_file TEXT REFERENCES songs(song_file) ON DELETE CASCADE,
        track_number INTEGER NOT NULL,
        PRIMARY KEY (album_slug, song_file)
    );
    """,
    # 13. Mixtapes
    """
    CREATE TABLE IF NOT EXISTS mixtapes (
        slug TEXT PRIMARY KEY,
        mixtape_name TEXT NOT NULL,
        description TEXT
    );
    """,
    # 14. Mixtape Songs link
    """
    CREATE TABLE IF NOT EXISTS mixtape_songs (
        mixtape_slug TEXT REFERENCES mixtapes(slug) ON DELETE CASCADE,
        song_file TEXT REFERENCES songs(song_file) ON DELETE CASCADE,
        track_number INTEGER NOT NULL,
        PRIMARY KEY (mixtape_slug, song_file)
    );
    """,
    # 15. Mixtape Genres link
    """
    CREATE TABLE IF NOT EXISTS mixtape_genres (
        mixtape_slug TEXT REFERENCES mixtapes(slug) ON DELETE CASCADE,
        genre_id INTEGER REFERENCES genres(id) ON DELETE CASCADE,
        PRIMARY KEY (mixtape_slug, genre_id)
    );
    """,
    # 16. Playlists
    """
    CREATE TABLE IF NOT EXISTS playlists (
        slug TEXT PRIMARY KEY,
        playlist_name TEXT NOT NULL,
        description TEXT
    );
    """,
    # 17. Playlist Songs link
    """
    CREATE TABLE IF NOT EXISTS playlist_songs (
        playlist_slug TEXT REFERENCES playlists(slug) ON DELETE CASCADE,
        song_file TEXT REFERENCES songs(song_file) ON DELETE CASCADE,
        track_number INTEGER NOT NULL,
        PRIMARY KEY (playlist_slug, song_file)
    );
    """,
    # 18. Playlist Genres link
    """
    CREATE TABLE IF NOT EXISTS playlist_genres (
        playlist_slug TEXT REFERENCES playlists(slug) ON DELETE CASCADE,
        genre_id INTEGER REFERENCES genres(id) ON DELETE CASCADE,
        PRIMARY KEY (playlist_slug, genre_id)
    );
    """,
    # 19. Playlist Moods link
    """
    CREATE TABLE IF NOT EXISTS playlist_moods (
        playlist_slug TEXT REFERENCES playlists(slug) ON DELETE CASCADE,
        mood_id INTEGER REFERENCES moods(id) ON DELETE CASCADE,
        PRIMARY KEY (playlist_slug, mood_id)
    );
    """,
    # 20. Sample Packs
    """
    CREATE TABLE IF NOT EXISTS sample_packs (
        slug TEXT PRIMARY KEY,
        pack_name TEXT NOT NULL,
        description TEXT
    );
    """,
    # 21. Samples
    """
    CREATE TABLE IF NOT EXISTS samples (
        file_path TEXT PRIMARY KEY,
        sample_pack_slug TEXT REFERENCES sample_packs(slug) ON DELETE CASCADE,
        sample_name TEXT NOT NULL,
        genre_id INTEGER REFERENCES genres(id) ON DELETE SET NULL,
        tempo INTEGER,
        key_id INTEGER REFERENCES keys(id) ON DELETE SET NULL,
        scale_id INTEGER REFERENCES scales(id) ON DELETE SET NULL
    );
    """,
    # 22. Loop Packs
    """
    CREATE TABLE IF NOT EXISTS loop_packs (
        slug TEXT PRIMARY KEY,
        pack_name TEXT NOT NULL,
        description TEXT
    );
    """,
    # 23. Loops
    """
    CREATE TABLE IF NOT EXISTS loops (
        file_path TEXT PRIMARY KEY,
        loop_pack_slug TEXT REFERENCES loop_packs(slug) ON DELETE CASCADE,
        loop_name TEXT NOT NULL,
        genre_id INTEGER REFERENCES genres(id) ON DELETE SET NULL,
        tempo INTEGER,
        key_id INTEGER REFERENCES keys(id) ON DELETE SET NULL,
        scale_id INTEGER REFERENCES scales(id) ON DELETE SET NULL
    );
    """,
    # 24. Stems
    """
    CREATE TABLE IF NOT EXISTS stems (
        slug TEXT PRIMARY KEY,
        stem_name TEXT NOT NULL,
        song_file TEXT REFERENCES songs(song_file) ON DELETE SET NULL
    );
    """,
    # 25. Stem Files
    """
    CREATE TABLE IF NOT EXISTS stem_files (
        file_path TEXT PRIMARY KEY,
        stem_slug TEXT REFERENCES stems(slug) ON DELETE CASCADE,
        track_name TEXT NOT NULL
    );
    """,
    # 26. Configuration
    """
    CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """,
    # 27. Tags
    """
    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tag_name TEXT UNIQUE NOT NULL
    );
    """,
    # 28. Song-Tag link
    """
    CREATE TABLE IF NOT EXISTS song_tags (
        song_file TEXT REFERENCES songs(song_file) ON DELETE CASCADE,
        tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
        PRIMARY KEY (song_file, tag_id)
    );
    """,
    # 29. Music Production Projects
    """
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name TEXT NOT NULL,
        project_path TEXT NOT NULL,
        entity_type TEXT NOT NULL CHECK(entity_type IN ('song', 'artist', 'album')),
        entity_id TEXT NOT NULL,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """,
)

SEED_KEYS = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")

SEED_SCALES = (
    "Major", "Minor", "Pentatonic", "Blues Scale", "Harmonic Minor",
    "Melodic Minor", "Dorian", "Phrygian", "Lydian", "Mixolydian",
    "Aeolian", "Locrian",
)

SEED_COUNTRIES = (
    "Vietnam", "United States", "United Kingdom", "Japan", "Germany",
    "France", "Russia", "South Korea", "Sweden", "Canada",
)

SEED_GENRES = (
    "Classical", "Lo-Fi", "Electronic", "Ambient", "Synthwave",
    "Hip Hop", "Rock", "Pop", "Jazz", "Cinematic", "Folk", "Sound Effects",
)

SEED_TAGS = (
    "AI Generated", "Instrumental", "Remix", "Cover", "Demo",
    "Acoustic", "Live", "Unreleased", "WIP", "Mastered",
)
