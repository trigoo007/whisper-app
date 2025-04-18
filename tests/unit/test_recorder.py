import pytest
from whisper_app.core.recorder import AudioRecorder
from whisper_app.core.config_manager import ConfigManager

class DummyConfig(ConfigManager):
    def __init__(self):
        super().__init__()
        self.config = self._get_default_config()

@pytest.fixture
def recorder():
    return AudioRecorder(DummyConfig())

def test_init(recorder):
    assert recorder.sample_rate == 16000
    assert recorder.channels == 1

def test_set_device(recorder):
    recorder.set_device(2)
    assert recorder.device_id == 2

def test_set_parameters(recorder):
    recorder.set_parameters(sample_rate=44100, channels=2)
    assert recorder.sample_rate == 44100
    assert recorder.channels == 2

def test_get_available_devices_error(monkeypatch, recorder):
    monkeypatch.setattr('sounddevice.query_devices', lambda: (_ for _ in ()).throw(Exception('fail')))
    assert recorder.get_available_devices() == [] 