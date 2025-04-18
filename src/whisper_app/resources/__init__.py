#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recursos para WhisperApp

Incluye:
- Traducciones
- Íconos
- Otros archivos estáticos
"""

import os

# Rutas a recursos
ICONS_PATH = os.path.join(os.path.dirname(__file__), "icons")
TRANSLATIONS_PATH = os.path.join(os.path.dirname(__file__), "translations")

def get_icon_path(icon_name):
    """
    Obtiene la ruta completa a un ícono
    
    Args:
        icon_name (str): Nombre del archivo de ícono
        
    Returns:
        str: Ruta completa al ícono
    """
    return os.path.join(ICONS_PATH, icon_name)

def get_translation_path(locale):
    """
    Obtiene la ruta completa a un archivo de traducción
    
    Args:
        locale (str): Código de idioma (ej: 'es', 'en')
        
    Returns:
        str: Ruta completa al archivo de traducción
    """
    return os.path.join(TRANSLATIONS_PATH, f"{locale}.qm")