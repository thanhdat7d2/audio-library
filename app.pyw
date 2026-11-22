"""Windows console-less GUI launcher for Audio Library Manager."""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from audio_library.app import launch


if __name__ == "__main__":
    launch()
