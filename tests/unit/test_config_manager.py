import pytest
import tempfile
import os
import json
from whisper_app.core.config_manager import ConfigManager

def test_config_read_write():
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        path = f.name
    try:
        cm = ConfigManager(config_file=path)
        cm.set('test_key', 'valor')
        cm2 = ConfigManager(config_file=path)
        assert cm2.get('test_key') == 'valor'
    finally:
        if os.path.exists(path):
            os.unlink(path)

def test_config_reset():
    cm = ConfigManager()
    cm.set('test_key', 'valor')
    cm.reset()
    assert cm.get('test_key') is None

def test_config_corrupt_file():
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
        f.write('{corrupt json')
        path = f.name
    try:
        cm = ConfigManager(config_file=path)
        # Debe cargar config por defecto
        assert isinstance(cm.get('model_size'), str)
    finally:
        if os.path.exists(path):
            os.unlink(path) 