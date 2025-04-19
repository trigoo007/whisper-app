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
from typing import Optional, Dict, Any

from whisper_app.utils import ffmpeg_utils, audio_utils, text_utils
from whisper_app.models import TranscriptionResult
from whisper_app.core.config_manager import ConfigManager
from whisper_app.core.exceptions import (
    FileProcessingError, FFMpegError, ConfigError, WhisperAppError
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

    def import_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Importa y procesa un archivo de audio/video.
        Convierte a WAV mono 16kHz si es necesario.

        Args:
            file_path (str): Ruta al archivo original.

        Returns:
            dict: Información del archivo importado (ruta, duración, etc.) o None si hay error.

        Raises:
            FileNotFoundError: Si el archivo original no existe.
            FileProcessingError: Si hay un error durante la importación o procesamiento.
            FFMpegError: Si FFMPEG es necesario y falla.
            ConfigError: Si hay un error al acceder a la configuración.
        """
        if not os.path.exists(file_path):
            msg = f"El archivo no existe: {file_path}"
            logger.error(msg)
            raise FileNotFoundError(msg)

        file_ext = Path(file_path).suffix.lower()
        if file_ext not in self.supported_extensions:
            msg = f"Formato de archivo no soportado: {file_path}"
            logger.error(msg)
            raise FileProcessingError(msg)

        if not ffmpeg_utils.check_ffmpeg():
            # FFMPEG es necesario para casi cualquier cosa que no sea WAV puro
            if file_ext != '.wav':
                msg = "FFMPEG no encontrado, es necesario para procesar este formato de archivo"
                logger.error(msg)
                raise FFMpegError(msg)
            else:
                # Podría ser un WAV no estándar, FFMPEG aún podría ser necesario más tarde
                logger.warning("FFMPEG no encontrado, la importación de WAV podría fallar si no es estándar.")

        # Verificar espacio en disco (aproximado)
        try:
            # ... (código de verificación de espacio)
        except OSError as e:
            msg = f"Error al verificar espacio en disco: {e}"
            logger.error(msg)
            raise FileProcessingError(msg) from e

        if not self._has_enough_space(file_path):
            msg = "Espacio en disco insuficiente para importar archivo"
            logger.error(msg)
            raise FileProcessingError(msg)

        processed_file_path = None
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp(prefix="whisper_import_")
            target_filename = f"imported_audio_{Path(file_path).stem}.wav"
            processed_file_path = os.path.join(temp_dir, target_filename)

            logger.info(f"Importando archivo: {file_path}")
            self.signals.status_update.emit(f"Importando: {Path(file_path).name}")

            # Convertir a WAV 16kHz mono usando FFMPEG si es necesario
            # La función convert_to_wav ya maneja FileNotFoundError y FFMpegError
            ffmpeg_utils.convert_to_wav(file_path, processed_file_path)

            if not os.path.exists(processed_file_path):
                 # Esto no debería ocurrir si convert_to_wav no lanzó excepción
                 raise FileProcessingError(f"Archivo procesado no encontrado después de la conversión: {processed_file_path}")

            # Obtener información del archivo procesado
            duration = ffmpeg_utils.get_duration(processed_file_path)
            if duration is None:
                # get_duration ahora devuelve None en lugar de lanzar excepción en caso de error
                logger.warning(f"No se pudo obtener la duración del archivo procesado: {processed_file_path}")
                # Podríamos lanzar un error o continuar con duración desconocida
                # raise FileProcessingError(f"No se pudo obtener la duración de {processed_file_path}")

            file_info = {
                "original_path": file_path,
                "processed_path": processed_file_path,
                "duration": duration,
                "size": os.path.getsize(processed_file_path),
                "format": "wav"
            }

            logger.info(f"Archivo importado exitosamente a: {processed_file_path}")
            self.signals.status_update.emit("Archivo importado")
            self.signals.file_imported.emit(file_info)

            # Devolver file_info para uso interno si es necesario
            return file_info

        except (FileNotFoundError, FFMpegError, FileProcessingError, ConfigError) as e:
            # Errores específicos ya conocidos, relanzar
            logger.error(f"Error durante la importación: {e}", exc_info=True)
            # Limpiar parcialmente si es posible
            if processed_file_path and os.path.exists(processed_file_path):
                try: os.remove(processed_file_path)
                except OSError: pass
            if temp_dir and os.path.exists(temp_dir):
                try: shutil.rmtree(temp_dir)
                except OSError: pass
            raise # Relanzar la excepción capturada

        except Exception as e:
            # Errores inesperados
            logger.error(f"Error inesperado durante la importación: {e}", exc_info=True)
            if processed_file_path and os.path.exists(processed_file_path):
                try: os.remove(processed_file_path)
                except OSError: pass
            if temp_dir and os.path.exists(temp_dir):
                try: shutil.rmtree(temp_dir)
                except OSError: pass
            # Envolver en FileProcessingError
            raise FileProcessingError(f"Error inesperado al importar: {e}") from e

    def export_transcription(self, transcription: TranscriptionResult, output_path: str, format: str):
        """
        Exporta la transcripción a un formato específico.

        Args:
            transcription (TranscriptionResult): Objeto con los datos de la transcripción.
            output_path (str): Ruta base para el archivo de salida (sin extensión).
            format (str): Formato de exportación ('txt', 'srt', 'vtt', 'json').

        Raises:
            FileProcessingError: Si la transcripción está vacía, el formato no es soportado,
                                 o hay errores de escritura o espacio en disco.
            ValueError: Si el formato no es válido.
        """
        if not transcription or not transcription.segments:
            msg = "Transcripción vacía, no se puede exportar"
            logger.error(msg)
            raise FileProcessingError(msg)

        if format not in self.export_formats:
            msg = f"Formato de exportación no soportado: {format}"
            logger.error(msg)
            raise ValueError(msg) # Usar ValueError para formato inválido

        output_file = f"{output_path}.{format}"

        # Verificar espacio en disco (estimación simple)
        estimated_size = len(transcription.text) * 2 # Estimación muy burda
        try:
            statvfs = os.statvfs(os.path.dirname(output_file))
            available_space = statvfs.f_frsize * statvfs.f_bavail
            if estimated_size > available_space:
                msg = "Espacio en disco insuficiente para exportar transcripción"
                logger.error(msg)
                raise FileProcessingError(msg)
        except OSError as e:
            msg = f"Error al verificar espacio en disco para exportación: {e}"
            logger.error(msg)
            raise FileProcessingError(msg) from e

        logger.info(f"Exportando transcripción a: {output_file} (formato: {format})" )
        self.signals.status_update.emit(f"Exportando a {format.upper()}...")

        try:
            exporter = getattr(text_utils, f"export_to_{format}")
            exporter(transcription, output_file)

            logger.info(f"Transcripción exportada exitosamente a {output_file}")
            self.signals.status_update.emit(f"Exportado a {format.upper()}")
            self.signals.export_finished.emit(output_file, format)

        except AttributeError:
            # Esto no debería ocurrir si self.export_formats está sincronizado con text_utils
            msg = f"Función de exportación no encontrada para el formato: {format}"
            logger.error(msg)
            raise ValueError(msg) # Error de programación, formato inválido
        except (IOError, OSError) as e:
            # Errores de escritura
            msg = f"Error de E/S al exportar transcripción a {output_file}: {e}"
            logger.error(msg, exc_info=True)
            raise FileProcessingError(msg) from e
        except Exception as e:
            # Otros errores inesperados (p.ej., dentro de text_utils)
            msg = f"Error inesperado al exportar transcripción: {e}"
            logger.error(msg, exc_info=True)
            raise FileProcessingError(msg) from e

    def _process_audio_file(self, file_path: str, temp_dir: str) -> str:
        """
        Procesa un archivo de audio: aplica normalización y/o VAD si están configurados.
        Devuelve la ruta al archivo procesado (puede ser el original).

        Args:
            file_path (str): Ruta al archivo WAV importado.
            temp_dir (str): Directorio temporal para archivos intermedios.

        Returns:
            str: Ruta al archivo de audio listo para transcribir.

        Raises:
            FFMpegError: Si FFMPEG falla durante el procesamiento.
            FileProcessingError: Si ocurren otros errores de procesamiento.
            ConfigError: Si hay error al leer la configuración.
        """
        processed_path = file_path
        needs_cleanup = []

        try:
            normalize = self.config.get("audio_normalize", False)
            use_vad = self.config.get("audio_vad", False)

            if normalize:
                logger.debug("Normalizando audio...")
                self.signals.status_update.emit("Normalizando audio...")
                try:
                    # normalize_audio ahora lanza excepciones
                    normalized_file = audio_utils.normalize_audio(processed_path, temp_dir)
                    if normalized_file != processed_path:
                        needs_cleanup.append(processed_path) # Marcar original para borrar si normalización tuvo éxito
                    processed_path = normalized_file
                    logger.debug(f"Audio normalizado: {processed_path}")
                except (FFMpegError, FileProcessingError) as norm_err:
                    # Error en normalización no es fatal, continuar con archivo anterior
                    logger.warning(f"Error al normalizar audio (continuando sin normalizar): {norm_err}")
                    # No añadir a needs_cleanup, no se creó archivo nuevo

            if use_vad:
                logger.debug("Aplicando VAD...")
                self.signals.status_update.emit("Aplicando VAD...")
                try:
                    # apply_vad ahora lanza excepciones
                    vad_file = audio_utils.apply_vad(processed_path, temp_dir)
                    if vad_file != processed_path:
                         # Marcar archivo anterior (normalizado o original) para borrar si VAD tuvo éxito
                        needs_cleanup.append(processed_path)
                    processed_path = vad_file
                    logger.debug(f"VAD aplicado: {processed_path}")
                except (FFMpegError, FileProcessingError) as vad_err:
                    # Error en VAD no es fatal, continuar con archivo anterior
                    logger.warning(f"Error al aplicar VAD (continuando sin VAD): {vad_err}")
                    # No añadir a needs_cleanup

            return processed_path

        except ConfigError as e:
            logger.error(f"Error al leer configuración de procesamiento de audio: {e}")
            raise # Relanzar error de configuración
        except Exception as e:
            # Capturar otros errores inesperados
            logger.error(f"Error inesperado procesando audio: {e}", exc_info=True)
            raise FileProcessingError(f"Error inesperado procesando audio: {e}") from e
        finally:
            # Limpiar archivos intermedios que ya no se necesitan
            for f in needs_cleanup:
                if f and os.path.exists(f) and f != file_path: # No borrar el importado original
                    try:
                        os.remove(f)
                        logger.debug(f"Archivo intermedio eliminado: {f}")
                    except OSError as e:
                        logger.warning(f"Error al eliminar archivo intermedio {f}: {e}")

    def cleanup_temp_files(self):
        """Limpia los archivos temporales generados por FileManager."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    logger.debug(f"Archivo temporal eliminado: {temp_file}")
            except Exception as e:
                logger.warning(f"Error al eliminar archivo temporal {temp_file}: {e}")
        
        self.temp_files = []

    def _has_enough_space(self, input_file_path: str) -> bool:
        """Estima si hay suficiente espacio para importar y procesar."""
        try:
            total, used, free = shutil.disk_usage(os.path.dirname(os.path.abspath(input_file_path)))
            required_space = os.path.getsize(input_file_path) * 2  # Estimación simple
            return free > required_space
        except OSError as e:
            logger.error(f"No se pudo verificar el espacio en disco: {e}")
            # Asumir que no hay espacio suficiente si no se puede verificar
            return False