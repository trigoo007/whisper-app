import pytest
import numpy as np
import tempfile
import os
from whisper_app.utils import audio_utils

def test_load_audio_nonexistent():
    assert audio_utils.load_audio('no_existe.wav') is None

def test_save_and_load_audio():
    arr = np.random.uniform(-1, 1, 16000).astype(np.float32)
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        path = f.name
    try:
        assert audio_utils.save_audio(arr, path)
        loaded = audio_utils.load_audio(path)
        assert loaded is not None
        assert isinstance(loaded, np.ndarray)
    finally:
        if os.path.exists(path):
            os.unlink(path)

def test_normalize_audio_invalid():
    # Debe lanzar RuntimeError si el archivo no existe
    with pytest.raises(RuntimeError):
        audio_utils.normalize_audio('no_existe.wav')

def test_normalize_audio():
    # Crear un archivo de audio de prueba con valores bajos
    arr = np.random.uniform(-0.1, 0.1, 16000).astype(np.float32)
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        path = f.name
    
    try:
        assert audio_utils.save_audio(arr, path)
        # Normalizar el audio
        normalized_path = audio_utils.normalize_audio(path)
        assert normalized_path is not None
        assert os.path.exists(normalized_path)
        
        # Verificar que el audio normalizado tiene mayor amplitud
        normalized_audio = audio_utils.load_audio(normalized_path)
        assert normalized_audio is not None
        assert np.max(np.abs(normalized_audio)) > np.max(np.abs(arr))
    finally:
        # Limpiar archivos
        if os.path.exists(path):
            os.unlink(path)
        if 'normalized_path' in locals() and os.path.exists(normalized_path):
            os.unlink(normalized_path)