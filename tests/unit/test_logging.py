import pytest
import logging
import os
import tempfile
from whisper_app.utils.log_config import setup_logging

def test_setup_logging():
    """Verificar que la configuración de logging funciona correctamente"""
    # Crear un directorio temporal para los logs
    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = os.path.join(temp_dir, "test_log.log")
        
        # Configurar logging
        logger = setup_logging(log_file)
        
        # Verificar que el logger existe
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        
        # Enviar algunos mensajes de log
        test_message = "Test message for logging"
        logger.info(test_message)
        
        # Verificar que el archivo de log existe y contiene el mensaje
        assert os.path.exists(log_file)
        with open(log_file, 'r') as f:
            content = f.read()
            assert test_message in content
