import pytest
import tempfile
import os
from whisper_app.core.file_manager import FileManager
from whisper_app.core.config_manager import ConfigManager

class DummyConfig(ConfigManager):
    def __init__(self):
        super().__init__()
        self.config = self._get_default_config()
        self.config["export_directory"] = tempfile.gettempdir()

@pytest.fixture
def file_manager():
    return FileManager(DummyConfig())

def test_import_file_nonexistent(file_manager):
    assert file_manager.import_file('no_existe.mp3') is None

def test_import_file_unsupported(file_manager):
    with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
        path = f.name
    try:
        assert file_manager.import_file(path) is None
    finally:
        if os.path.exists(path):
            os.unlink(path)

def test_export_transcription_empty(file_manager):
    assert file_manager.export_transcription({}) == {} 