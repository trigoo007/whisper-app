"""
Módulo para transcripción en tiempo real para WhisperApp
"""

import os
import logging
import tempfile
import threading
import time
import queue
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

from whisper_app.utils.audio_utils import save_audio
from whisper_app.utils.text_utils import clean_text

logger = logging.getLogger(__name__)

class RealtimeTranscriberSignals(QObject):
    """Señales para comunicación durante transcripción en tiempo real"""
    progress = pyqtSignal(str)  # texto parcial
    finished = pyqtSignal(str)  # texto completo
    error = pyqtSignal(str)  # mensaje de error

class RealtimeTranscriber:
    """
    Transcriptor en tiempo real que procesa fragmentos de audio continuamente
    Utiliza el mismo modelo Whisper pero optimizado para procesamiento en streaming
    """
    def __init__(self, transcriber, config_manager):
        """
        Inicializa el transcriptor en tiempo real
        Args:
            transcriber: Instancia de Transcriber existente (reutiliza su modelo)
            config_manager: Instancia de ConfigManager
        """
        self.transcriber = transcriber
        self.config = config_manager
        self.signals = RealtimeTranscriberSignals()
        self.audio_queue = queue.Queue()
        self.audio_buffer = np.array([], dtype=np.float32)
        self.window_size = 4.0  # segundos
        self.step_size = 2.0  # segundos
        self.sample_rate = 16000
        self.is_active = False
        self.processing_thread = None
        self.accumulated_text = ""

    def start(self):
        """Inicia el procesamiento en tiempo real"""
        if self.is_active:
            logger.warning("El transcriptor en tiempo real ya está activo")
            return
        if not self.transcriber.model:
            logger.error("No hay modelo cargado para transcripción en tiempo real")
            self.signals.error.emit("No hay modelo cargado para transcripción en tiempo real")
            return
        self.audio_buffer = np.array([], dtype=np.float32)
        self.accumulated_text = ""
        self.is_active = True
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        logger.info("Transcriptor en tiempo real iniciado")

    def stop(self):
        """Detiene el procesamiento en tiempo real"""
        if not self.is_active:
            return
        self.is_active = False
        if self.processing_thread:
            self.processing_thread.join(timeout=1.0)
            self.processing_thread = None
        if len(self.audio_buffer) > 0.5 * self.sample_rate:
            final_text = self._process_buffer(final=True)
            self.signals.finished.emit(final_text)
        else:
            self.signals.finished.emit(self.accumulated_text)
        logger.info("Transcriptor en tiempo real detenido")

    def add_audio_chunk(self, audio_chunk):
        """
        Añade un fragmento de audio al buffer
        Args:
            audio_chunk (np.ndarray): Fragmento de audio
        """
        if not self.is_active:
            return
        if audio_chunk.dtype != np.float32:
            audio_chunk = audio_chunk.astype(np.float32) / 32768.0
        self.audio_buffer = np.append(self.audio_buffer, audio_chunk)

    def _processing_loop(self):
        """Bucle principal de procesamiento"""
        last_process_time = time.time()
        while self.is_active:
            current_time = time.time()
            buffer_duration = len(self.audio_buffer) / self.sample_rate
            if (buffer_duration >= self.window_size and 
                (current_time - last_process_time) >= self.step_size):
                text = self._process_buffer()
                last_process_time = current_time
                if text:
                    self.signals.progress.emit(text)
            time.sleep(0.1)

    def _process_buffer(self, final=False):
        """
        Procesa el buffer actual y devuelve texto
        Args:
            final (bool): Si es la última llamada (todo el buffer)
        Returns:
            str: Texto transcrito
        """
        try:
            window_samples = int(self.window_size * self.sample_rate)
            if final:
                audio_window = self.audio_buffer
            else:
                if len(self.audio_buffer) > window_samples:
                    audio_window = self.audio_buffer[-window_samples:]
                else:
                    audio_window = self.audio_buffer
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                temp_path = f.name
            save_audio(audio_window, temp_path, self.sample_rate)
            try:
                options = {
                    "task": "transcribe",
                    "language": self.config.get("language"),
                    "beam_size": 1,
                    "best_of": 1,
                    "temperature": 0.0
                }
                result = self.transcriber.model.transcribe(temp_path, **options)
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                if final:
                    self.accumulated_text = result["text"].strip()
                    return self.accumulated_text
                new_text = result["text"].strip()
                if not new_text:
                    return self.accumulated_text
                if self.accumulated_text:
                    overlap_size = min(len(self.accumulated_text), len(new_text)) // 2
                    if overlap_size > 0:
                        best_overlap = 0
                        best_overlap_size = 0
                        for i in range(1, min(overlap_size, 10)):
                            last_words = ' '.join(self.accumulated_text.split()[-i:]).lower()
                            first_words = ' '.join(new_text.split()[:i]).lower()
                            if last_words in first_words or first_words in last_words:
                                if i > best_overlap_size:
                                    best_overlap_size = i
                                    best_overlap = i
                        if best_overlap > 0:
                            self.accumulated_text = self.accumulated_text + " " + " ".join(new_text.split()[best_overlap:])
                        else:
                            self.accumulated_text = self.accumulated_text + " " + new_text
                    else:
                        self.accumulated_text = self.accumulated_text + " " + new_text
                else:
                    self.accumulated_text = new_text
                self.accumulated_text = clean_text(self.accumulated_text)
                return self.accumulated_text
            except Exception as e:
                logger.error(f"Error al transcribir en tiempo real: {e}")
                return self.accumulated_text
        except Exception as e:
            logger.error(f"Error en procesamiento de buffer: {e}")
            return self.accumulated_text 