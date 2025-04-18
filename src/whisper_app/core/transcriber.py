#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Transcriptor para WhisperApp utilizando OpenAI Whisper
"""

import os
import logging
import tempfile
import math
import time
import subprocess
import whisper
from PyQt5.QtCore import QObject, pyqtSignal

# Añadir importación directa de verify_ffmpeg
from whisper_app.utils.ffmpeg_utils import verify_ffmpeg, get_file_duration
from whisper_app.utils.audio_utils import apply_vad

logger = logging.getLogger(__name__)

class TranscriptionSignals(QObject):
    """Señales para comunicación durante el proceso de transcripción"""
    progress = pyqtSignal(int, str)  # valor, mensaje
    finished = pyqtSignal(dict)  # resultado
    error = pyqtSignal(str)  # mensaje de error
    cancelled = pyqtSignal()  # señal de cancelación

class Transcriber(QObject):
    """Clase principal para transcripción utilizando Whisper"""
    
    def __init__(self, config_manager):
        """
        Inicializa el transcriptor
        
        Args:
            config_manager: Instancia de ConfigManager
        """
        super().__init__()
        self.config = config_manager
        self.model = None
        self.current_model_name = None
        self.cancel_requested = False
        self.signals = TranscriptionSignals()
    
    def load_model(self, model_name=None):
        """
        Carga el modelo de Whisper
        
        Args:
            model_name (str, optional): Nombre del modelo a cargar.
                Si es None, se utiliza el de la configuración.
        
        Returns:
            bool: True si se cargó correctamente, False en caso contrario
        """
        if model_name is None:
            model_name = self.config.get("model_size", "base")
        
        # Si el modelo ya está cargado, no hacer nada
        if self.model is not None and self.current_model_name == model_name:
            logger.info(f"Modelo '{model_name}' ya cargado")
            return True
        
        try:
            logger.info(f"Cargando modelo '{model_name}'...")
            self.signals.progress.emit(10, f"Cargando modelo '{model_name}'...")
            
            # Liberar memoria si hay un modelo anterior
            if self.model is not None:
                import gc
                del self.model
                gc.collect()
            
            # Cargar el nuevo modelo
            fp16 = self.config.get("fp16", True)
            self.model = whisper.load_model(model_name, fp16=fp16)
            self.current_model_name = model_name
            
            self.signals.progress.emit(100, f"Modelo '{model_name}' cargado con éxito")
            logger.info(f"Modelo '{model_name}' cargado con éxito")
            return True
            
        except Exception as e:
            self.model = None
            self.current_model_name = None
            error_msg = f"Error al cargar modelo '{model_name}': {e}"
            logger.error(error_msg)
            self.signals.error.emit(error_msg)
            return False
    
    def transcribe_file(self, file_path, language=None, translate_to=None):
        """
        Transcribe un archivo de audio/video
        
        Args:
            file_path (str): Ruta al archivo a transcribir
            language (str, optional): Código del idioma
            translate_to (str, optional): Código del idioma al que traducir
        
        Returns:
            dict: Resultado de la transcripción o None si hubo error
        """
        self.cancel_requested = False
        
        # Verificar que existe el archivo
        if not os.path.exists(file_path):
            error_msg = f"El archivo '{file_path}' no existe"
            logger.error(error_msg)
            self.signals.error.emit(error_msg)
            return None
        
        # Verificar FFMPEG
        if not verify_ffmpeg():
            error_msg = "FFMPEG no encontrado, es necesario para procesar archivos multimedia"
            logger.error(error_msg)
            self.signals.error.emit(error_msg)
            return None
        
        # Verificar que el modelo está cargado
        if self.model is None:
            if not self.load_model():
                return None
        
        # Estimar tiempo basado en duración y modelo
        try:
            duration = get_file_duration(file_path)
            if duration is not None:  # Verificar que duration no es None antes de usarlo
                # Estimación aproximada: más lento con modelos más grandes
                model_factor = {"tiny": 0.5, "base": 1.0, "small": 2.0, 
                                "medium": 3.0, "large": 5.0}
                factor = model_factor.get(self.current_model_name, 1.0)
                estimate = duration * factor / 60  # en minutos
                
                if estimate > 1:
                    self.signals.progress.emit(
                        5, 
                        f"Duración estimada: {estimate:.1f} minutos"
                    )
        except Exception as e:
            logger.warning(f"Error al estimar tiempo: {e}")
        
        # Determinar si el archivo es grande para procesarlo por segmentos
        large_file = False
        max_duration = 600  # 10 minutos
        
        if duration is not None and duration > max_duration:  # Verificar que duration no es None
            large_file = True
            self.signals.progress.emit(
                10, 
                f"Archivo grande ({duration/60:.1f} min). Se procesará por segmentos."
            )
        
        processed_file = file_path
        try:
            # Configurar opciones para Whisper
            options = self._prepare_whisper_options(language)
            
            # Aplicar VAD si está habilitado
            use_vad = self.config.get("use_vad", False)
            
            if use_vad:
                self.signals.progress.emit(15, "Aplicando detección de voz (VAD)...")
                processed_file = apply_vad(file_path)
                self.signals.progress.emit(20, "Detección de voz completada")
            
            # Transcribir
            start_time = time.time()
            
            if large_file:
                result = self._process_large_file(processed_file, options, max_duration)
            else:
                self.signals.progress.emit(25, "Transcribiendo audio...")
                result = self.model.transcribe(processed_file, **options)
                self.signals.progress.emit(75, "Transcripción completada")
            
            if self.cancel_requested:
                logger.info("Transcripción cancelada por el usuario")
                self.signals.cancelled.emit()
                # Limpiar archivo temporal si se usó VAD
                if use_vad and processed_file != file_path and os.path.exists(processed_file):
                    try:
                        os.unlink(processed_file)
                    except Exception as e:
                        logger.warning(f"Error al eliminar archivo temporal: {e}")
                return None
            
            elapsed = time.time() - start_time
            
            # Traducir si se solicitó
            translated = False
            if translate_to and not self.cancel_requested:
                self.signals.progress.emit(80, f"Traduciendo a {translate_to}...")
                
                # Guardar resultado original
                original_result = result
                
                # Configurar para traducción
                translate_options = options.copy()
                translate_options["task"] = "translate"
                translate_options["language"] = translate_to
                
                # Realizar traducción
                translation = self.model.transcribe(processed_file, **translate_options)
                
                # Actualizar resultado
                result = translation
                translated = True
                
                self.signals.progress.emit(95, "Traducción completada")
            
            # Emitir resultado
            output = {
                "result": result,
                "file": file_path,
                "time": elapsed,
                "translated": translated,
                "language_source": result.get("language", "unknown"),
                "language_target": translate_to if translated else None
            }
            
            self.signals.progress.emit(100, "Proceso completado con éxito")
            self.signals.finished.emit(output)
            
            return output
            
        except Exception as e:
            error_msg = f"Error durante la transcripción: {e}"
            logger.error(error_msg)
            self.signals.error.emit(error_msg)
            return None
        finally:
            # Limpiar archivo temporal si se usó VAD
            if use_vad and processed_file != file_path and os.path.exists(processed_file):
                try:
                    os.unlink(processed_file)
                except Exception as e:
                    logger.warning(f"Error al eliminar archivo temporal: {e}")
    
    def _prepare_whisper_options(self, language=None):
        """
        Prepara las opciones para Whisper
        
        Args:
            language (str, optional): Código del idioma
        
        Returns:
            dict: Opciones configuradas
        """
        options = {
            "task": "transcribe",
            "fp16": self.config.get("fp16", True),
            "beam_size": self.config.get("beam_size", 5),
            "best_of": self.config.get("best_of", 5)
        }
        
        # Configurar temperatura
        temperature = self.config.get("temperature", 0)
        if temperature > 0:
            options["temperature"] = temperature
        
        # Configurar idioma
        if language:
            options["language"] = language
        
        # Opciones avanzadas
        if self.config.get("suppress_tokens_no_speech", False):
            options["suppress_blank"] = True
        
        return options
    
    def _process_large_file(self, file_path, options, max_duration):
        """
        Procesa un archivo grande dividiéndolo en segmentos
        
        Args:
            file_path (str): Ruta al archivo
            options (dict): Opciones para Whisper
            max_duration (float): Duración máxima de cada segmento en segundos
        
        Returns:
            dict: Resultado combinado
        """
        # Obtener duración total
        duration = get_file_duration(file_path)
        if duration is None:
            # Si no se puede determinar la duración, usar un valor predeterminado
            duration = max_duration * 2
            logger.warning(f"No se pudo determinar la duración, usando valor predeterminado: {duration}s")
        
        # Crear directorio temporal
        temp_dir = tempfile.mkdtemp(prefix="whisper_segments_")
        segments = []
        
        try:
            # Dividir archivo en segmentos
            num_segments = math.ceil(duration / max_duration)
            
            for i in range(num_segments):
                if self.cancel_requested:
                    return None
                
                start = i * max_duration
                end = min((i + 1) * max_duration, duration)
                
                self.signals.progress.emit(
                    25 + (i * 25) // num_segments, 
                    f"Procesando parte {i+1}/{num_segments}..."
                )
                
                # Extraer segmento con ffmpeg
                segment_path = os.path.join(temp_dir, f"segment_{i:03d}.wav")
                
                ffmpeg_cmd = [
                    "ffmpeg", "-y", "-i", file_path,
                    "-ss", str(start), "-to", str(end),
                    "-ac", "1", "-ar", "16000",
                    segment_path
                ]
                
                subprocess.run(ffmpeg_cmd, capture_output=True, check=True)
                segments.append(segment_path)
            
            # Procesar cada segmento
            results = []
            offset = 0
            
            for i, segment in enumerate(segments):
                if self.cancel_requested:
                    return None
                
                self.signals.progress.emit(
                    50 + (i * 25) // len(segments),
                    f"Transcribiendo parte {i+1}/{len(segments)}..."
                )
                
                # Transcribir segmento
                result = self.model.transcribe(segment, **options)
                
                # Ajustar timestamps
                for seg in result["segments"]:
                    seg["start"] += offset
                    seg["end"] += offset
                
                results.append(result)
                offset += max_duration
            
            # Unificar resultados
            combined_result = {
                "text": " ".join(r["text"].strip() for r in results),
                "segments": [],
                "language": results[0]["language"] if results else None
            }
            
            for result in results:
                combined_result["segments"].extend(result["segments"])
            
            return combined_result
            
        finally:
            # Limpiar archivos temporales
            for segment in segments:
                try:
                    if os.path.exists(segment):
                        os.unlink(segment)
                except Exception as e:
                    logger.warning(f"Error al eliminar segmento temporal: {e}")
            
            try:
                os.rmdir(temp_dir)
            except Exception as e:
                logger.warning(f"Error al eliminar directorio temporal: {e}")
    
    def cancel(self):
        """Cancela el proceso de transcripción actual"""
        self.cancel_requested = True
        logger.info("Solicitud de cancelación recibida")