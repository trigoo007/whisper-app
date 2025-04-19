#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Grabador de audio para WhisperApp
"""

import os
import wave
import tempfile
import logging
import numpy as np
import sounddevice as sd
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from whisper_app.core.exceptions import RecordingError, FileProcessingError  # Importar excepciones

logger = logging.getLogger(__name__)

class RecorderSignals(QObject):
    """Señales para comunicación durante la grabación"""
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    recording_finished = pyqtSignal(str)  # ruta archivo
    recording_error = pyqtSignal(str, str)  # mensaje de error, tipo de error
    recording_level = pyqtSignal(float)  # nivel de audio (0-1)
    recording_time = pyqtSignal(int)  # tiempo en segundos
    recording_chunk = pyqtSignal(np.ndarray)  # fragmento de audio en tiempo real

class AudioRecorder(QObject):
    """Clase para la grabación de audio desde micrófono"""
    
    def __init__(self, config_manager):
        """
        Inicializa el grabador de audio
        
        Args:
            config_manager: Instancia de ConfigManager
        """
        super().__init__()
        self.config = config_manager
        self.signals = RecorderSignals()
        self.is_recording = False
        self.audio_data = []
        self.device_id = None
        self.sample_rate = self.config.get("sample_rate", 16000)
        self.channels = self.config.get("channels", 1)
        self.stream = None
        self.is_streaming = False  # Nueva bandera para modo streaming
        
        # Timer para actualizar tiempo de grabación
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_recording_time)
        self.start_time = 0
        self.recording_seconds = 0
        
        logger.debug(f"Grabador configurado: {self.sample_rate}Hz, {self.channels} canales")
    
    def _update_recording_time(self):
        """Actualiza y emite el tiempo de grabación"""
        if self.is_recording:
            self.recording_seconds += 1
            self.signals.recording_time.emit(self.recording_seconds)
    
    def set_device(self, device_id=None):
        """
        Establece el dispositivo de grabación
        
        Args:
            device_id: ID del dispositivo a utilizar (None para predeterminado)
        """
        self.device_id = device_id
        logger.debug(f"Dispositivo de grabación configurado: {device_id}")
    
    def set_parameters(self, sample_rate=None, channels=None):
        """
        Establece parámetros de grabación
        
        Args:
            sample_rate (int, optional): Frecuencia de muestreo
            channels (int, optional): Número de canales
        """
        if sample_rate is not None:
            self.sample_rate = sample_rate
            self.config.set("sample_rate", sample_rate)
        
        if channels is not None:
            self.channels = channels
            self.config.set("channels", channels)
        
        logger.debug(f"Parámetros actualizados: {self.sample_rate}Hz, {self.channels} canales")
    
    def get_available_devices(self):
        """
        Obtiene los dispositivos de entrada disponibles
        
        Returns:
            list: Lista de dispositivos disponibles

        Raises:
            RecordingError: Si ocurre un error al consultar los dispositivos.
        """
        try:
            devices = sd.query_devices()
            input_devices = []
            
            for idx, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    input_devices.append({
                        'id': idx,
                        'name': device['name'],
                        'channels': device['max_input_channels'],
                        'default': idx == sd.default.device[0]
                    })
            
            return input_devices
        except Exception as e:
            error_msg = f"Error al obtener dispositivos: {e}"
            logger.error(error_msg, exc_info=True)
            raise RecordingError(error_msg) from e

    def _cleanup_stream(self):
        """Detiene y cierra el stream de audio si está activo."""
        if self.stream:
            try:
                if not self.stream.closed:
                    self.stream.stop()
                    self.stream.close()
            except Exception as e:
                logger.warning(f"Error al cerrar el stream durante la limpieza: {e}")
            finally:
                self.stream = None
        self.is_recording = False
        self.is_streaming = False
        self.timer.stop()

    def start_recording(self):
        """
        Inicia la grabación de audio

        Raises:
            RecordingError: Si ya hay una grabación en curso o si ocurre un error al iniciar.
        """
        if self.is_recording:
            raise RecordingError("Ya hay una grabación en curso")

        try:
            # Reiniciar estado
            self.audio_data = []
            self.is_recording = True
            self.is_streaming = False # Asegurar que no está en modo streaming
            self.recording_seconds = 0

            logger.info("Iniciando grabación de audio...")

            # Función de callback para recibir datos de audio
            def audio_callback(indata, frames, time, status):
                """Callback para capturar audio"""
                if status:
                    # Solo loguear, no interrumpir grabación por warnings
                    logger.warning(f"Advertencia de estado en grabación: {status}")

                if self.is_recording and not self.is_streaming:
                    # Guardar datos de audio
                    self.audio_data.append(indata.copy())

                    # Calcular y emitir nivel de audio
                    if indata.size > 0:
                        try:
                            level = float(np.max(np.abs(indata))) / 32768.0 # Normalizar a 0-1
                            self.signals.recording_level.emit(level)
                        except Exception as lvl_err:
                            logger.warning(f"Error calculando nivel de audio: {lvl_err}")


            # Configurar y abrir stream de audio
            self.stream = sd.InputStream(
                device=self.device_id,
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype='int16', # Usar int16 comúnmente
                callback=audio_callback
            )

            self.stream.start()

            # Iniciar timer para actualizar tiempo
            self.timer.start(1000)  # cada segundo

            self.signals.recording_started.emit()
            logger.info("Grabación iniciada correctamente")

        except sd.PortAudioError as pa_err:
            error_msg = f"Error de PortAudio al iniciar grabación: {pa_err}"
            logger.error(error_msg, exc_info=True)
            self.signals.recording_error.emit(error_msg, RecordingError.__name__)
            self._cleanup_stream()
            raise RecordingError(error_msg) from pa_err
        except Exception as e:
            error_msg = f"Error inesperado al iniciar grabación: {e}"
            logger.error(error_msg, exc_info=True)
            self.signals.recording_error.emit(error_msg, RecordingError.__name__)
            self._cleanup_stream()
            raise RecordingError(error_msg) from e

    def stop_recording(self):
        """
        Detiene la grabación y guarda el archivo

        Returns:
            str: Ruta del archivo guardado

        Raises:
            RecordingError: Si no hay grabación en curso o no se capturó audio.
            FileProcessingError: Si ocurre un error al guardar el archivo.
        """
        if not self.is_recording or self.is_streaming: # No detener si está en modo streaming
            logger.warning("No hay grabación estándar en curso para detener")
            raise RecordingError("No hay grabación estándar en curso para detener")

        logger.info("Deteniendo grabación...")
        original_exception = None
        saved_file_path = None

        try:
            # Detener grabación y stream
            self.is_recording = False
            self.timer.stop()
            self._cleanup_stream() # Usa el helper

            self.signals.recording_stopped.emit()
            logger.info("Grabación detenida")

            # Verificar que hay datos grabados
            if not self.audio_data:
                error_msg = "No se capturó audio. Verifica el micrófono."
                logger.warning(error_msg)
                self.signals.recording_error.emit(error_msg, RecordingError.__name__)
                raise RecordingError(error_msg)

            # Guardar en archivo temporal
            try:
                with tempfile.NamedTemporaryFile(
                    suffix='.wav',
                    prefix='whisper_recording_',
                    delete=False
                ) as temp_file:
                    saved_file_path = temp_file.name
                    with wave.open(saved_file_path, 'wb') as wf:
                        wf.setnchannels(self.channels)
                        wf.setsampwidth(2)  # 16 bits
                        wf.setframerate(self.sample_rate)
                        # Concatenar y escribir datos
                        full_audio_data = np.concatenate(self.audio_data, axis=0)
                        wf.writeframes(full_audio_data.tobytes())

                logger.info(f"Grabación guardada en archivo temporal: {saved_file_path}")
                self.signals.recording_finished.emit(saved_file_path)
                return saved_file_path

            except (wave.Error, IOError, OSError) as e:
                error_msg = f"Error al guardar archivo de grabación: {e}"
                logger.error(error_msg, exc_info=True)
                self.signals.recording_error.emit(error_msg, FileProcessingError.__name__)
                raise FileProcessingError(error_msg) from e

        except Exception as e:
            # Captura cualquier otro error inesperado durante la detención
            original_exception = e
            error_msg = f"Error inesperado al detener grabación: {e}"
            logger.error(error_msg, exc_info=True)
            self.signals.recording_error.emit(error_msg, RecordingError.__name__)
            # Asegurar limpieza incluso si falla antes de guardar
            self._cleanup_stream()
            raise RecordingError(error_msg) from e

        finally:
            # Limpiar datos de audio después de intentar guardar o en caso de error
            self.audio_data = []

    def is_active(self):
        """
        Verifica si hay una grabación en curso
        
        Returns:
            bool: True si hay grabación en curso, False en caso contrario
        """
        return self.is_recording

    def start_streaming_recording(self):
        """
        Inicia grabación continua con envío de fragmentos en tiempo real.

        Raises:
            RecordingError: Si ya hay una grabación en curso o si ocurre un error al iniciar.
        """
        if self.is_recording:
             raise RecordingError("Ya hay una grabación en curso")
        try:
            # Reiniciar estado
            self.audio_data = [] # No acumularemos en modo streaming aquí
            self.is_recording = True
            self.is_streaming = True
            self.recording_seconds = 0
            # Tamaño del fragmento en muestras (ajustable, p.ej. 100ms)
            self.chunk_size = int(self.config.get("realtime_chunk_ms", 100) / 1000 * self.sample_rate)
            logger.info(f"Iniciando grabación en modo streaming (chunk: {self.chunk_size} samples)...")

            # Función de callback modificada para envío de fragmentos
            def audio_callback(indata, frames, time, status):
                """Callback para capturar audio y emitir fragmentos"""
                if status:
                    logger.warning(f"Advertencia de estado en grabación streaming: {status}")

                if self.is_recording and self.is_streaming:
                    # Emitir señal con el fragmento actual para procesamiento en tiempo real
                    # Asegurarse que es un array numpy plano
                    audio_chunk = indata.flatten().copy()
                    self.signals.recording_chunk.emit(audio_chunk)

                    # Calcular y emitir nivel de audio
                    if audio_chunk.size > 0:
                         try:
                            level = float(np.max(np.abs(audio_chunk))) / 32768.0 # Normalizar a 0-1
                            self.signals.recording_level.emit(level)
                         except Exception as lvl_err:
                            logger.warning(f"Error calculando nivel de audio en streaming: {lvl_err}")


            # Configurar y abrir stream de audio
            self.stream = sd.InputStream(
                device=self.device_id,
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype='int16',
                callback=audio_callback,
                blocksize=self.chunk_size # Usar blocksize para controlar tamaño de chunk
            )
            self.stream.start()
            # Iniciar timer para actualizar tiempo
            self.timer.start(1000)  # cada segundo
            self.signals.recording_started.emit()
            logger.info("Grabación en modo streaming iniciada correctamente")

        except sd.PortAudioError as pa_err:
            error_msg = f"Error de PortAudio al iniciar streaming: {pa_err}"
            logger.error(error_msg, exc_info=True)
            self.signals.recording_error.emit(error_msg, RecordingError.__name__)
            self._cleanup_stream()
            raise RecordingError(error_msg) from pa_err
        except Exception as e:
            error_msg = f"Error al iniciar grabación en streaming: {e}"
            logger.error(error_msg, exc_info=True)
            self.signals.recording_error.emit(error_msg, RecordingError.__name__)
            self._cleanup_stream()
            raise RecordingError(error_msg) from e

    def stop_streaming_recording(self):
        """Detiene la grabación en modo streaming."""
        if not self.is_recording or not self.is_streaming:
            logger.warning("No hay grabación en streaming en curso para detener")
            return # No lanzar error, simplemente no hacer nada si no está activo

        logger.info("Deteniendo grabación en streaming...")
        try:
            self.is_recording = False
            self.is_streaming = False
            self.timer.stop()
            self._cleanup_stream() # Usa el helper
            self.signals.recording_stopped.emit()
            logger.info("Grabación en streaming detenida.")
        except Exception as e:
            # Aunque _cleanup_stream maneja errores, capturamos aquí por si acaso
            error_msg = f"Error inesperado al detener grabación en streaming: {e}"
            logger.error(error_msg, exc_info=True)
            # No emitir señal de error aquí, ya que es una detención normal
            # pero sí asegurar la limpieza
            self._cleanup_stream()