#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WhisperApp - Aplicación de transcripción de audio/video utilizando OpenAI Whisper
"""

import sys
import os
import logging
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTranslator, QLocale

from whisper_app.ui.main_window import MainWindow
from whisper_app.core.config_manager import ConfigManager

# Configurar logging en ubicación estándar
logs_dir = None
if os.name == 'nt':  # Windows
    logs_dir = os.path.join(os.environ.get('APPDATA', ''), "WhisperApp", "logs")
else:  # Unix/Linux/Mac
    logs_dir = os.path.join(str(Path.home()), ".config", "whisper-app", "logs")

# Crear directorio de logs si no existe
if logs_dir:
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, "whisper_app.log")
else:
    log_file = os.path.join(os.path.expanduser("~"), "whisper_app.log")

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Punto de entrada principal de la aplicación"""
    try:
        # Inicializar aplicación Qt
        app = QApplication(sys.argv)
        app.setApplicationName("WhisperApp")
        app.setOrganizationName("WhisperApp")
        
        # Cargar configuración
        config = ConfigManager()
        
        # Configurar internacionalización
        translator = QTranslator()
        locale = config.get('language', QLocale.system().name())
        translator_path = os.path.join(
            os.path.dirname(__file__),
            'resources/translations',
            f"{locale}.qm"
        )
        if os.path.exists(translator_path):
            translator.load(translator_path)
            app.installTranslator(translator)
        
        # Crear y mostrar ventana principal
        window = MainWindow(config)
        window.show()
        
        logger.info("Aplicación iniciada correctamente")
        
        # Ejecutar bucle de eventos
        return app.exec_()
    
    except Exception as e:
        logger.error(f"Error al iniciar la aplicación: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())