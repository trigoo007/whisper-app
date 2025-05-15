#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestor de configuración para WhisperApp
"""

import os
import json
import logging
from typing import Any, Dict, Optional
from pathlib import Path
from datetime import datetime
from PyQt5.QtCore import QStandardPaths

from whisper_app.core.exceptions import ConfigError # Importar excepción
from whisper_app.utils.paths import APP_DATA_DIR, MODELS_DIR
from whisper_app.utils.paths import APP_DATA_DIR, MODELS_DIR

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
        self.config = self.load_config()
        
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
    
    def load_config(self) -> Dict[str, Any]:
        """
        Carga la configuración desde el archivo JSON.
        Si el archivo no existe o está corrupto, usa la configuración por defecto.

        Returns:
            dict: La configuración cargada o por defecto.

        Raises:
            ConfigError: Si hay un error grave al intentar leer el archivo.
        """
        if not os.path.exists(self.config_file):
            logger.info(f"Archivo de configuración no encontrado en {self.config_file}. Usando configuración por defecto.")
            # Guardar la configuración por defecto para crear el archivo
            try:
                self.save_config(self.default_config)
            except ConfigError as e:
                # Error al guardar el archivo por defecto, loguear pero continuar con defaults en memoria
                logger.error(f"No se pudo crear el archivo de configuración inicial: {e}")
            return self.default_config.copy()

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
            # Fusionar con defaults para asegurar que todas las claves existan
            config = self.default_config.copy()
            config.update(loaded_config)
            logger.info(f"Configuración cargada desde {self.config_file}")
            return config
        except json.JSONDecodeError as e:
            logger.warning(f"Error al decodificar JSON en {self.config_file}: {e}. Usando configuración por defecto.")
            # Intentar renombrar el archivo corrupto
            self._backup_corrupt_config()
            # Guardar la configuración por defecto
            try:
                self.save_config(self.default_config)
            except ConfigError as save_e:
                 logger.error(f"No se pudo guardar la configuración por defecto después de detectar archivo corrupto: {save_e}")
            return self.default_config.copy()
        except (IOError, OSError) as e:
            # Errores de lectura
            msg = f"Error de E/S al cargar configuración desde {self.config_file}: {e}"
            logger.error(msg, exc_info=True)
            # Lanzar excepción personalizada
            raise ConfigError(msg) from e
        except Exception as e:
            # Otros errores inesperados
            msg = f"Error inesperado al cargar configuración: {e}"
            logger.error(msg, exc_info=True)
            raise ConfigError(msg) from e
    
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
            "advanced_mode": False,
            "use_model_cache": True,
            "model_cache_dir": MODELS_DIR
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtiene un valor de la configuración.

        Args:
            key (str): Clave del valor a obtener.
            default (Any, optional): Valor por defecto si la clave no existe.

        Returns:
            Any: El valor de la configuración o el valor por defecto.
        """
        if self.config is None:
            logger.warning("Accediendo a configuración antes de cargarla. Usando valor por defecto.")
            return default
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """
        Establece un valor en la configuración y la guarda.

        Args:
            key (str): Clave del valor a establecer.
            value (Any): Nuevo valor.

        Raises:
            ConfigError: Si hay un error al guardar la configuración actualizada.
        """
        if self.config is None:
            logger.error("Intentando establecer configuración antes de cargarla.")
            # Podríamos inicializarla aquí o lanzar un error
            # self.config = self.default_config.copy()
            raise ConfigError("Configuración no inicializada al intentar establecer un valor.")

        self.config[key] = value
        # Guardar inmediatamente después de cambiar
        self.save_config()
    
    def update(self, config_dict):
        """
        Actualiza múltiples valores de configuración
        
        Args:
            config_dict (dict): Diccionario con configuraciones a actualizar
        """
        self.config.update(config_dict)
        self.save_config()
    
    def save_config(self, config: Optional[Dict[str, Any]] = None):
        """
        Guarda la configuración actual en el archivo JSON.

        Args:
            config (dict, optional): Configuración específica a guardar. Si es None, guarda self.config.

        Raises:
            ConfigError: Si hay un error al escribir el archivo.
        """
        config_to_save = config if config is not None else self.config
        if config_to_save is None:
             logger.warning("Intento de guardar configuración None.")
             return # O lanzar ConfigError si se considera un estado inválido

        try:
            # Asegurar que el directorio exista
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

            # Guardar de forma atómica (escribir en temporal y luego renombrar)
            temp_file_path = self.config_file + ".tmp"
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=4, ensure_ascii=False)
            
            # Reemplazar el archivo original con el temporal
            # En Windows, os.replace puede fallar si el archivo destino existe
            # Por eso, primero eliminamos el original si existe
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
            os.replace(temp_file_path, self.config_file)

            logger.debug(f"Configuración guardada correctamente en {self.config_file}")

        except (IOError, OSError) as e:
            msg = f"Error de E/S al guardar configuración en {self.config_file}: {e}"
            logger.error(msg, exc_info=True)
            # Intentar eliminar el archivo temporal si quedó
            if os.path.exists(temp_file_path):
                try: os.remove(temp_file_path)
                except OSError: pass
            raise ConfigError(msg) from e
        except Exception as e:
            # Otros errores inesperados (p.ej., error de serialización JSON)
            msg = f"Error inesperado al guardar configuración: {e}"
            logger.error(msg, exc_info=True)
            if os.path.exists(temp_file_path):
                try: os.remove(temp_file_path)
                except OSError: pass
            raise ConfigError(msg) from e
    
    def reset_to_defaults(self):
        """
        Restablece la configuración a los valores por defecto y la guarda.

        Raises:
            ConfigError: Si hay un error al guardar la configuración por defecto.
        """
        logger.info("Restableciendo configuración a valores por defecto.")
        self.config = self.default_config.copy()
        self.save_config()
    
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
        self.save_config()
    
    def _backup_corrupt_config(self):
        """Renombra un archivo de configuración corrupto para análisis."""
        if os.path.exists(self.config_file):
            try:
                backup_file = f"{self.config_file}.corrupt_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                os.rename(self.config_file, backup_file)
                logger.warning(f"Archivo de configuración corrupto renombrado a: {backup_file}")
            except (IOError, OSError) as e:
                logger.error(f"No se pudo renombrar el archivo de configuración corrupto: {e}")