#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestor de archivos para WhisperApp
"""

import os
import shutil
import tempfile
import logging
from datetime import datetime
from pathlib import Path

# Añadir importación directa de verify_ffmpeg
from whisper_app.utils.ffmpeg_utils import (
    verify_ffmpeg, 
    get_file_duration, 
    get_file_info,
    convert_to_wav
)
from whisper_app.utils.text_utils import (
    save_txt, 
    save_srt, 
    save_vtt
)

logger = logging.getLogger(__name__)

class FileManager:
    """Gestiona los archivos de audio/video y transcripciones"""
    
    def __init__(self, config_manager):
        """
        Inicializa el gestor de archivos
        
        Args:
            config_manager: Instancia de ConfigManager
        """
        self.config = config_manager
        self.temp_files = []  # Registrar archivos temporales
        
        # Formatos de archivo soportados
        self.supported_extensions = [
            # Audio
            '.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac', '.wma',
            # Video
            '.mp4', '.mov', '.avi', '.mkv', '.webm', '.wmv'
        ]
        
        # Asegurar que existe el directorio de exportación predeterminado
        export_dir = self.config.get("export_directory")
        if export_dir and not os.path.exists(export_dir):
            try:
                os.makedirs(export_dir, exist_ok=True)
            except Exception as e:
                logger.warning(f"No se pudo crear directorio de exportación: {e}")
    
    def __del__(self):
        """Limpia archivos temporales al destruir la instancia"""
        self.cleanup_temp_files()
    
    def is_supported_file(self, file_path):
        """
        Verifica si un archivo tiene formato soportado
        
        Args:
            file_path (str): Ruta al archivo
        
        Returns:
            bool: True si es soportado, False en caso contrario
        """
        ext = os.path.splitext(file_path.lower())[1]
        return ext in self.supported_extensions
    
    def get_supported_file_filter(self):
        """
        Obtiene filtro para diálogos de archivo
        
        Returns:
            str: Filtro para QFileDialog
        """
        audio_exts = [ext[1:] for ext in self.supported_extensions 
                      if ext in ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac', '.wma']]
        
        video_exts = [ext[1:] for ext in self.supported_extensions 
                      if ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.wmv']]
        
        audio_filter = f"Archivos de audio ({' '.join(['*.' + ext for ext in audio_exts])})"
        video_filter = f"Archivos de video ({' '.join(['*.' + ext for ext in video_exts])})"
        all_filter = f"Todos los archivos soportados ({' '.join(['*.' + ext[1:] for ext in self.supported_extensions])})"
        
        return f"{all_filter};;{audio_filter};;{video_filter};;Todos los archivos (*.*)"
    
    def _has_enough_disk_space(self, path, min_bytes=100*1024*1024):
        """Verifica si hay suficiente espacio libre en disco (por defecto 100MB)"""
        try:
            total, used, free = shutil.disk_usage(os.path.dirname(os.path.abspath(path)))
            return free > min_bytes
        except Exception as e:
            logger.warning(f"No se pudo verificar el espacio en disco: {e}")
            return True  # No bloquear si no se puede verificar

    def import_file(self, file_path, normalize_audio=False):
        """
        Importa un archivo para procesamiento
        
        Args:
            file_path (str): Ruta al archivo a importar
            normalize_audio (bool): Si se debe normalizar el audio
        
        Returns:
            dict: Información del archivo o None si hubo error
        """
        if not os.path.exists(file_path):
            logger.error(f"El archivo no existe: {file_path}")
            return None
        
        if not self.is_supported_file(file_path):
            logger.error(f"Formato de archivo no soportado: {file_path}")
            return None
        
        # Verificamos directamente si FFMPEG está disponible
        if not verify_ffmpeg():
            logger.error("FFMPEG no encontrado, es necesario para procesar archivos")
            return None
        
        # Verificar espacio antes de crear temporales
        if not self._has_enough_disk_space(file_path):
            logger.error("Espacio en disco insuficiente para importar archivo")
            return None
        
        try:
            # Obtener información del archivo
            file_info = get_file_info(file_path)
            
            # Si es necesario, convertir/normalizar
            processed_path = file_path
            if normalize_audio:
                processed_path = self._normalize_audio(file_path)
                if processed_path != file_path:
                    self.temp_files.append(processed_path)
            
            # Añadir a archivos recientes
            self.config.add_recent_file(file_path)
            
            # Obtener duración de manera segura
            duration = get_file_duration(file_path)
            if duration is None:
                duration = 0.0  # Valor predeterminado si no se puede determinar
            
            # Crear y devolver información
            return {
                'original_path': file_path,
                'processed_path': processed_path,
                'name': os.path.basename(file_path),
                'size': os.path.getsize(file_path),
                'duration': duration,
                'created': datetime.fromtimestamp(os.path.getctime(file_path)),
                'modified': datetime.fromtimestamp(os.path.getmtime(file_path)),
                'info': file_info
            }
            
        except Exception as e:
            logger.error(f"Error al importar archivo: {e}")
            return None
    
    def export_transcription(self, transcription, base_path=None, formats=None):
        """
        Exporta una transcripción en diferentes formatos
        
        Args:
            transcription (dict): Resultado de la transcripción
            base_path (str, optional): Ruta base para guardar archivos
            formats (list, optional): Formatos a exportar (txt, srt, vtt)
        
        Returns:
            dict: Rutas de los archivos exportados por formato
        """
        if not transcription:
            logger.error("Transcripción vacía, no se puede exportar")
            return {}
        
        # Determinar formatos a exportar
        if formats is None:
            formats = self.config.get("export_formats", ["txt", "srt", "vtt"])
        
        # Determinar ruta base
        if base_path is None:
            # Usar directorio de exportación predeterminado
            export_dir = self.config.get("export_directory")
            if not export_dir or not os.path.isdir(export_dir):
                export_dir = os.path.join(str(Path.home()), "Transcripciones")
                os.makedirs(export_dir, exist_ok=True)
            
            # Generar nombre de archivo basado en la fecha y hora
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_path = os.path.join(export_dir, f"transcripcion_{timestamp}")
        
        # Verificar espacio antes de exportar
        if not self._has_enough_disk_space(base_path):
            logger.error("Espacio en disco insuficiente para exportar transcripción")
            return {}
        
        # Asegurar que el directorio existe
        os.makedirs(os.path.dirname(base_path), exist_ok=True)
        
        # Exportar cada formato solicitado
        result = {}
        
        try:
            if "txt" in formats:
                txt_path = save_txt(transcription, f"{base_path}.txt")
                result["txt"] = txt_path
            
            if "srt" in formats:
                srt_path = save_srt(transcription, f"{base_path}.srt")
                result["srt"] = srt_path
            
            if "vtt" in formats:
                vtt_path = save_vtt(transcription, f"{base_path}.vtt")
                result["vtt"] = vtt_path
            
            logger.info(f"Transcripción exportada a {base_path}.* en formatos: {', '.join(formats)}")
            return result
            
        except Exception as e:
            logger.error(f"Error al exportar transcripción: {e}")
            return result
    
    def _normalize_audio(self, file_path):
        """
        Normaliza audio para mejor transcripción
        
        Args:
            file_path (str): Ruta al archivo a normalizar
        
        Returns:
            str: Ruta al archivo normalizado
        """
        temp_file = None
        try:
            temp_file = tempfile.NamedTemporaryFile(
                suffix='.wav',
                prefix='whisper_normalized_',
                delete=False
            ).name
            try:
                normalized_path = convert_to_wav(
                    file_path, 
                    temp_file,
                    sample_rate=16000,
                    channels=1,
                    normalize=True
                )
            except Exception as e:
                logger.warning(f"Error al normalizar audio: {e}")
                # Limpiar archivo temporal en caso de error
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                    except Exception:
                        pass
                raise  # Propagar el error
            # Registrar el archivo temporal para limpieza posterior
            if normalized_path != file_path:
                self.temp_files.append(normalized_path)
            return normalized_path
        except Exception as e:
            logger.warning(f"Error al normalizar audio: {e}, usando original")
            return file_path
    
    def cleanup_temp_files(self):
        """Elimina archivos temporales"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    logger.debug(f"Archivo temporal eliminado: {temp_file}")
            except Exception as e:
                logger.warning(f"Error al eliminar archivo temporal {temp_file}: {e}")
        
        self.temp_files = []