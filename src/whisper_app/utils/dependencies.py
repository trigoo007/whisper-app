#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidades para manejar dependencias opcionales
"""

import importlib
import logging

logger = logging.getLogger(__name__)

def import_optional(module_name, package_name=None):
    """
    Intenta importar un módulo opcional.
    Retorna el módulo si tiene éxito, None si falla.

    Args:
        module_name (str): El nombre del módulo a importar (ej. "faster_whisper").
        package_name (str, optional): El nombre del paquete a instalar si es diferente
                                    del nombre del módulo (ej. "python-docx" para "docx").
                                    Si es None, se asume que es igual a module_name.
    Returns:
        module/None: El módulo importado o None si hay un ImportError.
    """
    if package_name is None:
        package_name = module_name
    try:
        return importlib.import_module(module_name)
    except ImportError:
        logger.warning(
            f"Módulo opcional '{module_name}' no encontrado. "
            f"Algunas funcionalidades pueden no estar disponibles. "
            f"Intenta instalarlo con: pip install {package_name}"
        )
        return None
    except Exception as e:
        logger.error(
            f"Error al importar módulo opcional '{module_name}': {e}",
            exc_info=True
        )
        return None
