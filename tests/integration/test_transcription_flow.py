import pytest
import tempfile
import numpy as np
import os
from whisper_app.core.transcriber import Transcriber
from whisper_app.core.config_manager import ConfigManager

class DummyModel:
    def transcribe(self, file_path, **options):
        return {"text": "esto es una prueba", "segments": [{"start": 0, "end": 1, "text": "esto es una prueba"}], "language": "es"}

@pytest.fixture
def transcriber():
    config = ConfigManager()
    t = Transcriber(config)
    t.model = DummyModel()
    t.current_model_name = "base"
    return t

def test_transcription_flow(transcriber):
    # Crear archivo de audio temporal
    arr = np.random.uniform(-1, 1, 16000).astype(np.float32)
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        path = f.name
    try:
        from whisper_app.utils.audio_utils import save_audio
        save_audio(arr, path)
        result = transcriber.transcribe_file(path)
        assert result is not None
        assert "result" in result
        assert "text" in result["result"]
        assert len(result["result"]["segments"]) > 0
    finally:
        if os.path.exists(path):
            os.unlink(path) 