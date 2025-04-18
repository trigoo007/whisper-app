import pytest
from whisper_app.core.transcriber import Transcriber
from whisper_app.core.config_manager import ConfigManager

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