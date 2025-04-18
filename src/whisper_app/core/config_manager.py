#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestor de configuración para WhisperApp
"""

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigManager:
    """Gestiona la configuración de la aplicación"""
    
    def __init__(self, config_file=None):
        """
        Inicializa el gestor de configuración
        
        Args:
            config_file (str, optional): Ruta al archivo de configuración.
                Si es None, se utiliza la ubicación predeterminada.
        """
        # Determinar la ruta del archivo de configuración
        if config_file is None:
            # Ubicación predeterminada según el sistema operativo
            config_dir = self._get_config_dir()
            self.config_file = os.path.join(config_dir, "whisper_app_config.json")
        else:
            self.config_file = config_file
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        # Cargar configuración existente o crear una nueva
        self.config = self._load_config()
        
        logger.debug(f"Configuración inicializada desde {self.config_file}")
    
    def _get_config_dir(self):
        """
        Determina el directorio de configuración según el sistema operativo
        
        Returns:
            str: Ruta al directorio de configuración
        """
        home = str(Path.home())
        
        if os.name == 'nt':  # Windows
            return os.path.join(home, "AppData", "Local", "WhisperApp")
        elif os.name == 'posix':  # Linux, macOS, etc.
            # Seguir estándar XDG para Linux
            xdg_config = os.environ.get('XDG_CONFIG_HOME')
            if xdg_config:
                return os.path.join(xdg_config, "whisper-app")
            else:
                return os.path.join(home, ".config", "whisper-app")
        else:
            # Fallback genérico
            return os.path.join(home, ".whisper-app")
    
    def _load_config(self):
        """
        Carga la configuración desde el archivo
        
        Returns:
            dict: Configuración cargada o configuración predeterminada
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error al cargar configuración: {e}")
                logger.info("Usando configuración predeterminada")
                return self._get_default_config()
        else:
            logger.info("Archivo de configuración no encontrado, usando valores predeterminados")
            return self._get_default_config()
    
    def _get_default_config(self):
        """
        Crea una configuración predeterminada
        
        Returns:
            dict: Configuración predeterminada
        """
        return {
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
            "advanced_mode": False
        }
    
    def get(self, key, default=None):
        """
        Obtiene un valor de configuración
        
        Args:
            key (str): Clave del valor a obtener
            default: Valor predeterminado si la clave no existe
        
        Returns:
            Valor de configuración o el valor predeterminado
        """
        return self.config.get(key, default)
    
    def set(self, key, value):
        """
        Establece un valor de configuración
        
        Args:
            key (str): Clave a establecer
            value: Valor a establecer
        """
        self.config[key] = value
        self.save()
    
    def update(self, config_dict):
        """
        Actualiza múltiples valores de configuración
        
        Args:
            config_dict (dict): Diccionario con configuraciones a actualizar
        """
        self.config.update(config_dict)
        self.save()
    
    def save(self):
        """Guarda la configuración actual en el archivo"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.debug("Configuración guardada correctamente")
        except Exception as e:
            logger.error(f"Error al guardar configuración: {e}")
    
    def reset(self):
        """Restablece la configuración a valores predeterminados"""
        self.config = self._get_default_config()
        self.save()
        logger.info("Configuración restablecida a valores predeterminados")
    
    def add_recent_file(self, file_path):
        """
        Añade un archivo a la lista de archivos recientes
        
        Args:
            file_path (str): Ruta del archivo a añadir
        """
        recent_files = self.config.get("recent_files", [])
        
        # Eliminar si ya existe (para moverlo al principio)
        if file_path in recent_files:
            recent_files.remove(file_path)
        
        # Añadir al principio
        recent_files.insert(0, file_path)
        
        # Limitar a los 10 más recientes
        self.config["recent_files"] = recent_files[:10]
        self.save()