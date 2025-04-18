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

logger = logging.getLogger(__name__)

class RecorderSignals(QObject):
    """Señales para comunicación durante la grabación"""
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    recording_finished = pyqtSignal(str)  # ruta archivo
    recording_error = pyqtSignal(str)  # mensaje de error
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
            logger.error(f"Error al obtener dispositivos: {e}")
            return []
    
    def start_recording(self):
        """
        Inicia la grabación de audio
        
        Returns:
            bool: True si se inició correctamente, False en caso contrario
        """
        if self.is_recording:
            logger.warning("Ya hay una grabación en curso")
            return False
        
        try:
            # Reiniciar estado
            self.audio_data = []
            self.is_recording = True
            self.recording_seconds = 0
            
            logger.info("Iniciando grabación de audio...")
            
            # Función de callback para recibir datos de audio
            def audio_callback(indata, frames, time, status):
                """Callback para capturar audio"""
                if status:
                    logger.warning(f"Error de estado en grabación: {status}")
                
                if self.is_recording:
                    # Guardar datos de audio
                    self.audio_data.append(indata.copy())
                    
                    # Calcular y emitir nivel de audio
                    if indata.size > 0:
                        level = float(np.max(np.abs(indata)))
                        self.signals.recording_level.emit(level)
            
            # Configurar y abrir stream de audio
            self.stream = sd.InputStream(
                device=self.device_id,
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype='int16',
                callback=audio_callback
            )
            
            self.stream.start()
            
            # Iniciar timer para actualizar tiempo
            self.timer.start(1000)  # cada segundo
            
            self.signals.recording_started.emit()
            logger.info("Grabación iniciada correctamente")
            return True
            
        except Exception as e:
            self.is_recording = False
            error_msg = f"Error al iniciar grabación: {e}"
            logger.error(error_msg)
            self.signals.recording_error.emit(error_msg)
            return False
    
    def stop_recording(self):
        """
        Detiene la grabación y guarda el archivo
        
        Returns:
            str: Ruta del archivo guardado o None si hubo error
        """
        if not self.is_recording:
            logger.warning("No hay grabación en curso para detener")
            return None
        
        try:
            # Detener grabación
            self.is_recording = False
            self.timer.stop()
            
            if self.stream:
                try:
                    self.stream.stop()
                    self.stream.close()
                except Exception as e:
                    logger.warning(f"Error al cerrar el stream: {e}")
                self.stream = None
            
            self.signals.recording_stopped.emit()
            logger.info("Grabación detenida")
            
            # Verificar que hay datos grabados
            if not self.audio_data:
                error_msg = "No se capturó audio. Verifica el micrófono."
                logger.warning(error_msg)
                self.signals.recording_error.emit(error_msg)
                return None
            
            # Guardar en archivo temporal
            temp_file = tempfile.NamedTemporaryFile(
                suffix='.wav',
                prefix='whisper_recording_',
                delete=False
            )
            
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 16 bits
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join([arr.tobytes() for arr in self.audio_data]))
            
            logger.info(f"Grabación guardada en archivo temporal: {temp_file.name}")
            self.signals.recording_finished.emit(temp_file.name)
            return temp_file.name
            
        except Exception as e:
            error_msg = f"Error al detener grabación: {e}"
            logger.error(error_msg)
            # Asegurar cierre del stream incluso en caso de error
            if self.stream:
                try:
                    self.stream.stop()
                    self.stream.close()
                except Exception:
                    pass
                self.stream = None
            self.signals.recording_error.emit(error_msg)
            return None
    
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
        Similar a start_recording() pero optimizado para streaming.
        Returns:
            bool: True si se inició correctamente, False en caso contrario
        """
        if self.is_recording:
            logger.warning("Ya hay una grabación en curso")
            return False
        try:
            # Reiniciar estado
            self.audio_data = []
            self.is_recording = True
            self.is_streaming = True  # Nueva bandera para modo streaming
            self.recording_seconds = 0
            # Tamaño del fragmento en muestras (20ms a 16kHz = 320 muestras)
            self.chunk_size = int(0.02 * self.sample_rate)
            logger.info("Iniciando grabación en modo streaming...")
            # Función de callback modificada para envío de fragmentos
            def audio_callback(indata, frames, time, status):
                """Callback para capturar audio y emitir fragmentos"""
                if status:
                    logger.warning(f"Error de estado en grabación: {status}")
                if self.is_recording:
                    # Guardar datos de audio
                    self.audio_data.append(indata.copy())
                    # Emitir señal con el fragmento actual para procesamiento en tiempo real
                    if hasattr(self.signals, 'recording_chunk'):
                        self.signals.recording_chunk.emit(indata.flatten())
                    # Calcular y emitir nivel de audio
                    if indata.size > 0:
                        level = float(np.max(np.abs(indata)))
                        self.signals.recording_level.emit(level)
            # Configurar y abrir stream de audio
            self.stream = sd.InputStream(
                device=self.device_id,
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype='int16',
                callback=audio_callback,
                blocksize=self.chunk_size
            )
            self.stream.start()
            # Iniciar timer para actualizar tiempo
            self.timer.start(1000)  # cada segundo
            self.signals.recording_started.emit()
            logger.info("Grabación en modo streaming iniciada correctamente")
            return True
        except Exception as e:
            self.is_recording = False
            self.is_streaming = False
            error_msg = f"Error al iniciar grabación en streaming: {e}"
            logger.error(error_msg)
            self.signals.recording_error.emit(error_msg)
            return False

    def is_streaming(self):
        """
        Verifica si hay una grabación en modo streaming activa
        Returns:
            bool: True si hay grabación en streaming, False en caso contrario
        """
        return hasattr(self, 'is_streaming') and self.is_streaming