#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WhisperApp - Aplicación de transcripción de audio/video utilizando OpenAI Whisper
"""

import sys
import os
import logging
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTranslator, QLocale

from whisper_app.ui.main_window import MainWindow
from whisper_app.core.config_manager import ConfigManager
from whisper_app.ui.styles import apply_theme
from whisper_app.core.exceptions import WhisperAppError
from whisper_app.ui.dialogs import ErrorReportDialog

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

def show_error_dialog(message, trace=None):
    """Muestra un diálogo de error cuando no es posible iniciar la GUI completa"""
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    if 'ErrorReportDialog' in globals():
        try:
            dialog = ErrorReportDialog(message, trace)
            dialog.exec_()
        except Exception:
            # Fallback si el diálogo personalizado falla
            QMessageBox.critical(None, "Error crítico", message)
    else:
        QMessageBox.critical(None, "Error crítico", message)
    
    return app.exit(1)

def check_critical_dependencies():
    import importlib
    import shutil
    missing = []
    optional_missing = []
    version_issues = []
    
    # Dependencias de Python con versiones mínimas
    min_versions = {
        "torch": "1.8.0",
        "numpy": "1.20.0",
        "soundfile": "0.10.0",
        "scipy": "1.6.0",
        "sounddevice": "0.4.0",
        "PyQt5": "5.15.0"
    }
    
    for pkg, min_ver in min_versions.items():
        try:
            module = importlib.import_module(pkg)
            if hasattr(module, '__version__'):
                current_ver = module.__version__
                # Comparación simple de versiones
                if current_ver.split('.') < min_ver.split('.'):
                    version_issues.append(f"{pkg} (versión {current_ver}, mínima {min_ver})")
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
    
    if missing or version_issues:
        msg = "\n\nProblemas con dependencias críticas para ejecutar WhisperApp:\n\n"
        
        if missing:
            msg += "Dependencias faltantes:\n" + "\n".join(f"- {dep}" for dep in missing) + "\n\n"
        
        if version_issues:
            msg += "Versiones incompatibles:\n" + "\n".join(f"- {issue}" for issue in version_issues) + "\n\n"
            
        msg += "Por favor, instala/actualiza los paquetes y/o asegúrate de que FFMPEG esté en el PATH.\n"
        msg += "\nConsulta la sección 'Resolución de problemas' en el README para más información.\n"
        
        print(msg, file=sys.stderr)
        show_error_dialog(
            "No se pueden cargar dependencias críticas",
            msg
        )
        sys.exit(2)
    
    if optional_missing:
        msg = (
            "\n\nAlgunas dependencias opcionales no están instaladas:\n\n" +
            "\n".join(f"- {dep}" for dep in optional_missing) +
            "\n\nLa aplicación funcionará, pero algunas características podrían no estar disponibles.\n"
        )
        print(msg, file=sys.stderr)

def cleanup_resources():
    """Limpia recursos antes de cerrar la aplicación"""
    logger.info("Realizando limpieza de recursos...")
    try:
        # Limpiar archivos temporales si existen
        import tempfile
        import glob
        
        patterns = [
            os.path.join(tempfile.gettempdir(), "whisperapp_*.wav"),
            os.path.join(tempfile.gettempdir(), "whisperapp_*.mp3"),
            os.path.join(tempfile.gettempdir(), "whisperapp_*.json"),
        ]
        
        for pattern in patterns:
            for file in glob.glob(pattern):
                try:
                    if os.path.exists(file) and os.path.getsize(file) > 0:
                        os.unlink(file)
                        logger.debug(f"Archivo temporal eliminado: {file}")
                except Exception as e:
                    logger.warning(f"No se pudo eliminar archivo temporal {file}: {e}")
    except Exception as e:
        logger.error(f"Error durante la limpieza de recursos: {e}")

def main():
    """Punto de entrada principal de la aplicación"""
    app = None
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
        
        # Asegurar limpieza de recursos al salir
        app.aboutToQuit.connect(cleanup_resources)
        
        # Aplicar tema elegante oscuro por defecto o el configurado por el usuario
        theme = config.get('ui_theme', 'elegant_dark')
        apply_theme(app, theme)
        
        # Configurar internacionalización
        translator = QTranslator()
        locale = config.get('ui_language', QLocale.system().name())
        
        # Corregir ruta de los archivos de traducción
        try:
            from whisper_app.resources import TRANSLATIONS_PATH
            translator_path = os.path.join(
                TRANSLATIONS_PATH,
                f"{locale}.qm"
            )
            
            if os.path.exists(translator_path):
                translator.load(translator_path)
                app.installTranslator(translator)
                logger.debug(f"Archivo de traducción cargado: {translator_path}")
            else:
                # Intentar cargar traducción por defecto (en_US)
                fallback_path = os.path.join(TRANSLATIONS_PATH, "en_US.qm")
                if os.path.exists(fallback_path):
                    translator.load(fallback_path)
                    app.installTranslator(translator)
                    logger.debug(f"Usando traducción por defecto: {fallback_path}")
        except Exception as e:
            logger.warning(f"Error al cargar traducciones: {e}")
        
        # Crear y mostrar ventana principal
        window = MainWindow(config)
        window.show()
        
        logger.info("Aplicación iniciada correctamente")
        
        # Ejecutar bucle de eventos
        return app.exec_()
    
    except WhisperAppError as e:
        logger.error(f"Error específico de WhisperApp: {e}", exc_info=True)
        trace = traceback.format_exc()
        return show_error_dialog(f"Error en la aplicación: {e}", trace)
    except Exception as e:
        logger.critical(f"Error no controlado: {e}", exc_info=True)
        trace = traceback.format_exc()
        return show_error_dialog(f"Error inesperado: {e}", trace)

if __name__ == "__main__":
    sys.exit(main())