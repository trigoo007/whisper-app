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

def check_critical_dependencies():
    import importlib
    import shutil
    missing = []
    # Dependencias de Python
    for pkg in ["torch", "numpy", "soundfile", "scipy", "sounddevice"]:
        try:
            importlib.import_module(pkg)
        except ImportError:
            missing.append(pkg)
    # FFMPEG
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg (binario)")
    if missing:
        msg = (
            "\n\nFaltan dependencias críticas para ejecutar WhisperApp:\n\n" +
            "\n".join(f"- {dep}" for dep in missing) +
            "\n\nPor favor, instala los paquetes y/o asegúrate de que FFMPEG esté en el PATH.\n"
        )
        print(msg, file=sys.stderr)
        sys.exit(2)

def main():
    """Punto de entrada principal de la aplicación"""
    try:
        check_critical_dependencies()
        # Inicializar aplicación Qt
        app = QApplication(sys.argv)
        app.setApplicationName("WhisperApp")
        app.setOrganizationName("WhisperApp")
        
        # Cargar configuración
        config = ConfigManager()
        
        # Configurar internacionalización
        translator = QTranslator()
        locale = config.get('ui_language', QLocale.system().name())
        
        # Corregir ruta de los archivos de traducción
        from whisper_app.resources import TRANSLATIONS_PATH
        translator_path = os.path.join(
            TRANSLATIONS_PATH,
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