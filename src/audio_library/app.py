import os
import re
import socket
import threading
from pathlib import Path

import mutagen
import webview
from bottle import Bottle, response, static_file

from . import database
from .api import AudioLibraryAPI

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = PROJECT_ROOT / "web"
INCLUDE_PATTERN = re.compile(r"<!--\s*include:([a-zA-Z0-9_./-]+)\s*-->")


def render_index_html() -> str:
    """Renders web/index.html by inlining modular HTML partials."""
    html = (WEB_DIR / "index.html").read_text(encoding="utf-8")

    def _replace(match):
        rel_path = match.group(1)
        partial_path = (WEB_DIR / rel_path).resolve()
        if WEB_DIR.resolve() in partial_path.parents and partial_path.is_file():
            return partial_path.read_text(encoding="utf-8")
        return ""

    return INCLUDE_PATTERN.sub(_replace, html)


def extract_embedded_cover(audio_path: str) -> tuple[bytes, str] | None:
    """Extracts embedded album artwork bytes and MIME type from MP3/FLAC/OGG files."""
    if not audio_path or not os.path.exists(audio_path):
        return None
    try:
        audio = mutagen.File(audio_path)
        if not audio:
            return None
        # ID3 APIC (MP3 / WAV with ID3)
        if hasattr(audio, "tags") and audio.tags:
            for key, tag in audio.tags.items():
                if str(key).startswith("APIC") and hasattr(tag, "data"):
                    return tag.data, getattr(tag, "mime", "image/jpeg") or "image/jpeg"
        # FLAC pictures
        if hasattr(audio, "pictures") and audio.pictures:
            pic = audio.pictures[0]
            return pic.data, pic.mime or "image/jpeg"
    except Exception:
        pass
    return None


def find_free_port() -> int:
    """Finds an available localhost TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def create_app(api_bridge: AudioLibraryAPI) -> Bottle:
    """Creates and configures the Bottle application serving UI and media assets."""
    app = Bottle()

    @app.route("/")
    def index():
        response.content_type = "text/html; charset=utf-8"
        return render_index_html()

    @app.route("/css/<filename:path>")
    def serve_css(filename):
        return static_file(filename, root=str(WEB_DIR / "css"))

    @app.route("/js/<filename:path>")
    def serve_js(filename):
        return static_file(filename, root=str(WEB_DIR / "js"))

    @app.route("/media/song/<filename>")
    def serve_song(filename):
        if api_bridge.library_path:
            return static_file(filename, root=os.path.join(api_bridge.library_path, "song"))
        return "Library not set", 404

    @app.route("/media/song-cover/<song_file>")
    def serve_song_cover(song_file):
        if not api_bridge.library_path or not api_bridge.db_path:
            return "Library not set", 404
        conn = database.get_db_connection(api_bridge.db_path)
        try:
            row = conn.execute(
                """
                SELECT COALESCE(s.audio_file, CASE WHEN s.has_audio = 1 THEN s.song_file ELSE NULL END) as audio_file,
                       al.album_cover
                FROM songs s
                LEFT JOIN album_songs als ON s.song_file = als.song_file
                LEFT JOIN albums al ON als.album_slug = al.slug
                WHERE s.song_file = ?
                """,
                (song_file,),
            ).fetchone()
        finally:
            conn.close()

        if not row:
            response.status = 404
            return ""

        if row["album_cover"]:
            cover_abs = os.path.join(api_bridge.library_path, row["album_cover"])
            if os.path.isfile(cover_abs):
                return static_file(os.path.basename(cover_abs), root=os.path.dirname(cover_abs))

        if row["audio_file"]:
            embedded = extract_embedded_cover(os.path.join(api_bridge.library_path, "song", row["audio_file"]))
            if embedded:
                data, mime = embedded
                response.content_type = mime
                response.set_header("Cache-Control", "public, max-age=86400")
                return data

        response.status = 404
        return ""

    @app.route("/media/artist/<slug>/<filename>")
    def serve_artist_asset(slug, filename):
        if api_bridge.library_path:
            return static_file(filename, root=os.path.join(api_bridge.library_path, "artist", slug))
        return "Library not set", 404

    @app.route("/media/album/<slug>/<filename>")
    def serve_album_asset(slug, filename):
        if api_bridge.library_path:
            return static_file(filename, root=os.path.join(api_bridge.library_path, "album", slug))
        return "Library not set", 404

    return app


def launch() -> None:
    """Starts the local Bottle media/UI server and opens the native WebView window."""
    api_bridge = AudioLibraryAPI()
    app = create_app(api_bridge)
    port = find_free_port()

    server_thread = threading.Thread(
        target=app.run,
        kwargs={"host": "127.0.0.1", "port": port, "quiet": True},
        daemon=True,
    )
    server_thread.start()

    webview.create_window(
        "Audio Library Manager",
        f"http://127.0.0.1:{port}",
        js_api=api_bridge,
        width=1280,
        height=820,
        min_size=(900, 600),
        background_color="#090c12",
    )
    webview.start()
