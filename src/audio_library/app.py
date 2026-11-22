import os
import re
import socket
import threading
from pathlib import Path

import webview
from bottle import Bottle, response, static_file

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
        width=1200,
        height=800,
        min_size=(900, 600),
        background_color="#0f172a",
    )
    webview.start()
