import pytest
from whisper_app.core.transcriber import Transcriber
from whisper_app.core.config_manager import ConfigManager
import os

class DummyConfig(ConfigManager):
    def __init__(self):
        super().__init__()
        self.config = self._get_default_config()

@pytest.fixture
def transcriber():
    config = DummyConfig()
    return Transcriber(config)

def test_load_model_success(transcriber):
    # Debe cargar el modelo por defecto sin lanzar excepción
    assert transcriber.load_model() is True

def test_load_model_invalid(transcriber):
    # Si se pasa un modelo inexistente, debe devolver False
    assert transcriber.load_model("modelo_inexistente") is False

def test_transcribe_file_nonexistent(transcriber):
    result = transcriber.transcribe_file('no_existe.wav')
    assert result is None

def test_transcribe_file_no_ffmpeg(monkeypatch, transcriber, tmp_path):
    # Simular verify_ffmpeg devolviendo False
    monkeypatch.setattr('whisper_app.utils.ffmpeg_utils.verify_ffmpeg', lambda: False)
    fake_file = tmp_path / "test.wav"
    fake_file.write_bytes(b"data")
    result = transcriber.transcribe_file(str(fake_file))
    assert result is None

def test_transcribe_file_no_model(monkeypatch, transcriber, tmp_path):
    # Simular modelo no cargado y load_model fallando
    transcriber.model = None
    monkeypatch.setattr(transcriber, 'load_model', lambda *a, **kw: False)
    fake_file = tmp_path / "test.wav"
    fake_file.write_bytes(b"data")
    result = transcriber.transcribe_file(str(fake_file))
    assert result is None 