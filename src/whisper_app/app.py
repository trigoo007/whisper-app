#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WhisperApp - Aplicación de transcripción de audio/video utilizando OpenAI Whisper
"""

import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTranslator, QLocale

from whisper_app.ui.main_window import MainWindow
from whisper_app.core.config_manager import ConfigManager
from whisper_app.ui.styles import apply_theme
from whisper_app.core.exceptions import WhisperAppError

# Configurar logging en ubicación estándar
logs_dir = None
if os.name == 'nt':  # Windows
    logs_dir = os.path.join(os.environ.get('APPDATA', ''), "WhisperApp", "logs")
else:  # Unix/Linux/Mac
    logs_dir = os.path.join(str(Path.home()), ".config", "whisper-app", "logs")

# Crear directorio de logs si no existe
log_file = None
try:
    if logs_dir:
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, "whisper_app.log")
    else:
        log_file = os.path.join(os.path.expanduser("~"), "whisper_app.log")
except PermissionError:
    # Si no se puede crear el directorio, usar un directorio temporal
    import tempfile
    log_file = os.path.join(tempfile.gettempdir(), "whisper_app.log")
    print(f"No se pudo crear el directorio de logs. Usando archivo temporal: {log_file}", file=sys.stderr)

# Configurar logging
try:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3),  # 5MB por archivo, máximo 3 archivos
            logging.StreamHandler()
        ]
    )
except Exception as e:
    print(f"Error al configurar logging: {e}", file=sys.stderr)
    # Configuración mínima de respaldo
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])

logger = logging.getLogger(__name__)

def check_critical_dependencies():
    import importlib
    import shutil
    missing = []
    optional_missing = []
    
    # Dependencias de Python
    for pkg in ["torch", "numpy", "soundfile", "scipy", "sounddevice"]:
        try:
            importlib.import_module(pkg)
        except ImportError:
            missing.append(pkg)
    
    # Dependencias opcionales
    for pkg in ["pydub"]:
        try:
            importlib.import_module(pkg)
        except ImportError:
            optional_missing.append(pkg)
    
    # FFMPEG
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg (binario)")
    
    if missing:
        msg = (
            "\n\nFaltan dependencias críticas para ejecutar WhisperApp:\n\n" +
            "\n".join(f"- {dep}" for dep in missing) +
            "\n\nPor favor, instala los paquetes y/o asegúrate de que FFMPEG esté en el PATH.\n" +
            "\nConsulta la sección 'Resolución de problemas' en el README para más información.\n"
        )
        print(msg, file=sys.stderr)
        sys.exit(2)
    
    if optional_missing:
        msg = (
            "\n\nAlgunas dependencias opcionales no están instaladas:\n\n" +
            "\n".join(f"- {dep}" for dep in optional_missing) +
            "\n\nLa aplicación funcionará, pero algunas características podrían no estar disponibles.\n"
        )
        print(msg, file=sys.stderr)

def main():
    """Punto de entrada principal de la aplicación"""
    try:
        # Cargar configuración primero para permitir configurar nivel de logs
        config = ConfigManager()
        
        # Ajustar nivel de logging según configuración
        log_level = config.get('log_level', 'INFO').upper()
        try:
            numeric_level = getattr(logging, log_level)
            logging.getLogger().setLevel(numeric_level)
        except (AttributeError, TypeError):
            logger.warning(f"Nivel de log inválido: {log_level}. Usando INFO.")
            logging.getLogger().setLevel(logging.INFO)
        
        check_critical_dependencies()
        # Inicializar aplicación Qt
        app = QApplication(sys.argv)
        app.setApplicationName("WhisperApp")
        app.setOrganizationName("WhisperApp")
        
        # Aplicar tema elegante oscuro por defecto o el configurado por el usuario
        theme = config.get('ui_theme', 'elegant_dark')
        apply_theme(app, theme)
        
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