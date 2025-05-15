#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de instalación para WhisperApp
Descarga modelos de Whisper, verifica dependencias y configura la aplicación
"""

import os
import sys
import argparse
import logging
import json
import subprocess
import tempfile
from pathlib import Path

# Asegurar que podemos importar desde whisper_app
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from src.whisper_app.utils.paths import MODELS_DIR, APP_DATA_DIR
except ImportError:
    # Definir rutas por defecto si no se puede importar desde whisper_app
    from datetime import datetime
    
    def get_app_data_dir():
        home = os.path.expanduser("~")
        return os.path.join(home, ".whisperapp")

    APP_DATA_DIR = get_app_data_dir()
    MODELS_DIR = os.path.join(APP_DATA_DIR, "models")
    
    # Crear directorios si no existen
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("install")

def check_dependencies():
    """
    Verifica las dependencias necesarias para WhisperApp
    
    Returns:
        bool: True si todas las dependencias están disponibles, False en caso contrario
    """
    logger.info("Verificando dependencias...")
    
    # Lista de dependencias
    dependencies = [
        "torch",
        "whisper",
        "PyQt5",
        "sounddevice",
        "numpy",
    ]
    
    missing = []
    
    # Verificar cada dependencia
    for dep in dependencies:
        try:
            __import__(dep)
            logger.info(f"✓ {dep}")
        except ImportError:
            logger.warning(f"✗ {dep}")
            missing.append(dep)
    
    # Verificar FFmpeg
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"✓ ffmpeg")
        else:
            missing.append("ffmpeg")
            logger.warning(f"✗ ffmpeg")
    except FileNotFoundError:
        missing.append("ffmpeg")
        logger.warning(f"✗ ffmpeg")
    
    if missing:
        logger.warning("Dependencias faltantes: " + ", ".join(missing))
        logger.warning("Puedes instalarlas con los siguientes comandos:")
        
        # Mostrar comandos para instalar las dependencias faltantes
        if any(dep for dep in missing if dep != "ffmpeg"):
            pip_deps = [dep for dep in missing if dep != "ffmpeg"]
            logger.warning(f"pip install {' '.join(pip_deps)}")
        
        if "ffmpeg" in missing:
            logger.warning("Para instalar ffmpeg:")
            logger.warning("- En Windows: https://ffmpeg.org/download.html")
            logger.warning("- En macOS: brew install ffmpeg")
            logger.warning("- En Ubuntu/Debian: sudo apt install ffmpeg")
        
        return False
    
    logger.info("Todas las dependencias están instaladas.")
    return True

def download_whisper_model(model_name="base", device="auto"):
    """
    Descarga un modelo de Whisper si no está disponible localmente
    
    Args:
        model_name (str): Nombre del modelo (tiny, base, small, medium, large)
        device (str): Dispositivo para cargar el modelo (cpu, cuda, auto)
    
    Returns:
        bool: True si el modelo está disponible, False en caso contrario
    """
    logger.info(f"Verificando modelo {model_name}...")
    
    # Usar el directorio de modelos configurado
    download_dir = MODELS_DIR
    os.makedirs(download_dir, exist_ok=True)
    
    # Configurar la variable de entorno XDG_CACHE_HOME para que whisper use nuestro directorio
    os.environ["XDG_CACHE_HOME"] = download_dir
    
    try:
        # Importar whisper y descargar el modelo
        import whisper
        logger.info(f"Descargando modelo {model_name} en {download_dir}...")
        whisper.load_model(model_name, device=device, download_root=download_dir)
        logger.info(f"Modelo {model_name} disponible en {download_dir}")
        return True
    except Exception as e:
        logger.error(f"Error al descargar el modelo {model_name}: {e}")
        return False

def create_config(overwrite=False):
    """
    Crea o actualiza el archivo de configuración de WhisperApp
    
    Args:
        overwrite (bool): Si es True, sobrescribe la configuración existente
    
    Returns:
        bool: True si se creó o actualizó la configuración, False en caso contrario
    """
    config_dir = APP_DATA_DIR
    config_file = os.path.join(config_dir, "whisper_app_config.json")
    
    # Verificar si el archivo ya existe
    if os.path.exists(config_file) and not overwrite:
        logger.info(f"Archivo de configuración ya existe en {config_file}")
        logger.info("Use --force para sobrescribirlo")
        return False
    
    # Configuración predeterminada
    config = {
        "model_size": "base",
        "language": None,  # Detección automática
        "export_formats": ["txt", "srt", "vtt"],
        "auto_export": False,
        "export_directory": str(Path.home() / "Documents" / "WhisperApp"),
        "ffmpeg_path": None,  # Auto-detectar
        "sample_rate": 16000,
        "channels": 1,
        "beam_size": 5,
        "temperature": 0,
        "best_of": 5,
        "fp16": True,
        "use_vad": False,
        "recent_files": [],
        "ui_theme": "system",
        "ui_language": "auto",
        "advanced_mode": False,
        "use_model_cache": True,
        "model_cache_dir": MODELS_DIR
    }
    
    try:
        # Crear directorio si no existe
        os.makedirs(config_dir, exist_ok=True)
        
        # Guardar configuración
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        
        logger.info(f"Configuración guardada en {config_file}")
        return True
    except Exception as e:
        logger.error(f"Error al guardar la configuración: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Instalar y configurar WhisperApp")
    
    parser.add_argument("--check", action="store_true",
                      help="Verificar dependencias")
    
    parser.add_argument("--model", choices=["tiny", "base", "small", "medium", "large", "all"],
                      default="base", help="Modelo a descargar (default: base)")
    
    parser.add_argument("--config", action="store_true",
                      help="Crear o actualizar configuración")
    
    parser.add_argument("--force", action="store_true",
                      help="Sobrescribir archivos existentes")
    
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"],
                      default="auto", help="Dispositivo para cargar el modelo (default: auto)")
    
    args = parser.parse_args()
    
    # Mostrar las rutas de directorios
    logger.info(f"Directorio de datos: {APP_DATA_DIR}")
    logger.info(f"Directorio de modelos: {MODELS_DIR}")
    
    # Si no se especifican opciones, verificar dependencias
    if not (args.check or args.model or args.config):
        args.check = True
        args.model = "base"
        args.config = True
    
    # Verificar dependencias
    if args.check:
        if not check_dependencies():
            logger.warning("Algunas dependencias no están disponibles.")
            # Continuar con la instalación
    
    # Descargar modelo
    if args.model:
        if args.model == "all":
            models = ["tiny", "base", "small", "medium", "large"]
            for model in models:
                download_whisper_model(model, args.device)
        else:
            download_whisper_model(args.model, args.device)
    
    # Crear configuración
    if args.config:
        create_config(args.force)
    
    logger.info("Instalación completada.")

if __name__ == "__main__":
    main()
