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
            audio_to_process = np.array([], dtype=np.float32) # Inicializar

            if final:
                # Procesar todo el buffer restante
                if len(self.audio_buffer) > 0:
                    audio_to_process = self.audio_buffer
                    self.audio_buffer = np.array([], dtype=np.float32) # Limpiar buffer
                else:
                    return self.accumulated_text # No hay nada que procesar
            else:
                # Procesar una ventana deslizante
                # Asegurarse de tener suficientes datos para una ventana completa
                if len(self.audio_buffer) >= window_samples:
                    # Tomar la última ventana de audio
                    audio_to_process = self.audio_buffer[-window_samples:]
                    # Avanzar el buffer eliminando la parte procesada (step_size)
                    step_samples = int(self.step_size * self.sample_rate)
                    # Conservar solo la parte que no se solapa completamente
                    # Esto es una simplificación, la lógica de solapamiento real está en el texto
                    # Mantenemos el buffer para la siguiente ventana
                    # self.audio_buffer = self.audio_buffer[step_samples:] # <- Esta línea podría ser problemática, mejor manejar el solapamiento en el texto
                else:
                    # No hay suficientes datos para una ventana completa todavía
                    return self.accumulated_text

            if audio_to_process.size == 0:
                 return self.accumulated_text

            # Transcribir directamente desde el array numpy
            try:
                options = {
                    "task": "transcribe",
                    "language": self.config.get("language"), # Usar el idioma configurado globalmente
                    "beam_size": 1, # Optimizado para velocidad en tiempo real
                    "best_of": 1,
                    "temperature": 0.0, # Más determinista
                    "fp16": self.config.get("fp16", True) # Usar fp16 si está configurado
                    # Considerar añadir 'prompt' o 'prefix' si se quiere guiar la transcripción
                    # "prompt": self.accumulated_text[-50:] # Ejemplo: usar las últimas 50 chars como prompt
                }
                # Asegurar que el modelo está disponible
                if not self.transcriber or not self.transcriber.model:
                    logger.error("Modelo no disponible para transcripción en tiempo real.")
                    self.signals.error.emit("Modelo no disponible.")
                    return self.accumulated_text

                # Ejecutar transcripción
                result = self.transcriber.model.transcribe(audio_to_process, **options)

                new_text = result["text"].strip()
                logger.debug(f"Realtime chunk processed. New text: '{new_text}'")

                if final:
                    # Si es final, simplemente añadir el último fragmento
                    if new_text:
                         # Lógica simple de solapamiento para la parte final
                        if self.accumulated_text and new_text:
                            # Buscar si las últimas palabras del acumulado están al inicio del nuevo
                            overlap_found = False
                            for i in range(min(5, len(self.accumulated_text.split()), len(new_text.split())), 0, -1):
                                last_words_accum = " ".join(self.accumulated_text.split()[-i:]).lower()
                                first_words_new = " ".join(new_text.split()[:i]).lower()
                                if last_words_accum == first_words_new:
                                    self.accumulated_text += " " + " ".join(new_text.split()[i:])
                                    overlap_found = True
                                    break
                            if not overlap_found:
                                self.accumulated_text += " " + new_text
                        elif new_text:
                            self.accumulated_text = new_text
                    self.accumulated_text = clean_text(self.accumulated_text)
                    logger.info(f"Realtime finished. Final text: '{self.accumulated_text}'")
                    return self.accumulated_text
                else:
                    # Lógica de acumulación y solapamiento para progreso
                    if not new_text:
                        return self.accumulated_text # No añadir nada si está vacío

                    if self.accumulated_text:
                        # Lógica de solapamiento mejorada (buscar coincidencia más larga)
                        best_overlap_len = 0
                        # Iterar desde un solapamiento potencial razonable hasta 1 palabra
                        max_possible_overlap = min(len(self.accumulated_text.split()), len(new_text.split()), 10) # Limitar a 10 palabras
                        for i in range(max_possible_overlap, 0, -1):
                            last_words = " ".join(self.accumulated_text.split()[-i:]).lower()
                            first_words = " ".join(new_text.split()[:i]).lower()
                            # Ser más flexible con la coincidencia (ignorar mayúsculas/minúsculas)
                            if last_words == first_words:
                                best_overlap_len = i
                                break # Encontrar la coincidencia más larga y parar

                        if best_overlap_len > 0:
                            # Añadir solo la parte no solapada
                            words_to_add = new_text.split()[best_overlap_len:]
                            if words_to_add:
                                self.accumulated_text += " " + " ".join(words_to_add)
                        else:
                            # Si no hay solapamiento claro, añadir todo (podría repetirse)
                            # Opcional: Podríamos intentar una heurística más simple si no hay solapamiento
                            # Por ejemplo, si el nuevo texto es muy corto, podría ser una corrección
                            if len(new_text.split()) < 3 and len(self.accumulated_text.split()) > 0:
                                # Podría ser una corrección de la última palabra, intentar reemplazar
                                pass # Por ahora, simplemente añadimos
                            self.accumulated_text += " " + new_text
                    else:
                        # Primer fragmento de texto
                        self.accumulated_text = new_text

                    self.accumulated_text = clean_text(self.accumulated_text)
                    logger.debug(f"Realtime progress. Accumulated text: '{self.accumulated_text}'")
                    # Avanzar el buffer eliminando la parte procesada (step_size)
                    step_samples = int(self.step_size * self.sample_rate)
                    if len(self.audio_buffer) >= step_samples:
                         self.audio_buffer = self.audio_buffer[step_samples:]

                    return self.accumulated_text

            except Exception as e:
                # Log detallado del error de transcripción
                logger.error(f"Error al transcribir fragmento en tiempo real: {e}", exc_info=True)
                # No emitir señal de error aquí para no interrumpir continuamente
                # self.signals.error.emit(f"Error transcripción: {e}")
                return self.accumulated_text # Devolver texto acumulado hasta ahora

        except Exception as e:
            logger.error(f"Error general en procesamiento de buffer: {e}", exc_info=True)
            self.signals.error.emit(f"Error procesamiento: {e}")
            return self.accumulated_text