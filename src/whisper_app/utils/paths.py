#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidades para manejo de rutas en WhisperApp
"""

import os
import logging
from pathlib import Path
from PyQt5.QtCore import QStandardPaths

logger = logging.getLogger(__name__)

def get_app_data_dir():
    """
    Obtiene el directorio de datos de la aplicación
    
    Returns:
        str: Ruta al directorio de datos
    """
    # Usar QStandardPaths para obtener el directorio estándar según el sistema operativo
    app_data_location = QStandardPaths.standardLocations(QStandardPaths.AppDataLocation)
    if app_data_location:
        base_dir = os.path.join(app_data_location[0], "WhisperApp")
    else:
        # Fallback a directorio en home
        base_dir = os.path.expanduser("~/.whisperapp")
    
    # Asegurar que el directorio existe
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

# Definir rutas principales
APP_DATA_DIR = get_app_data_dir()
MODELS_DIR = os.path.join(APP_DATA_DIR, "models")
CACHE_DIR = os.path.join(APP_DATA_DIR, "cache")
TEMP_DIR = os.path.join(APP_DATA_DIR, "temp")

# Asegurar que los directorios principales existan
for directory in [MODELS_DIR, CACHE_DIR, TEMP_DIR]:
    os.makedirs(directory, exist_ok=True)
    logger.debug(f"Directorio creado/verificado: {directory}")

def get_model_path(model_name):
    """
    Obtiene la ruta completa a un modelo
    
    Args:
        model_name (str): Nombre del modelo (ej. 'base', 'small', 'medium')
    
    Returns:
        str: Ruta completa al modelo
    """
    return os.path.join(MODELS_DIR, model_name)
