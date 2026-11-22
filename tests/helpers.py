"""Shared test fixtures and helpers."""

import sys
import tempfile
import unittest
import wave
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from audio_library.api import AudioLibraryAPI


def create_silent_wav(path: Path, duration_sec: float = 1.0, sample_rate: int = 8000) -> None:
    """Creates a minimal valid PCM WAV file for testing audio import & duration extraction."""
    num_frames = int(duration_sec * sample_rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_frames)


class BaseLibraryTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.library_dir = self.root / "library"
        self.config_file = self.root / "app_settings.json"
        self.api = AudioLibraryAPI(config_file=self.config_file)

    def tearDown(self):
        self.temp_dir.cleanup()
