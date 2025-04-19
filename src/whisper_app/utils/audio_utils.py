#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidades para procesamiento de audio en WhisperApp
"""

import os
import logging
import tempfile
import subprocess
import numpy as np
from pathlib import Path

# Importar módulos al inicio del archivo
try:
    import soundfile as sf
except ImportError:
    sf = None
    logging.warning("El módulo 'soundfile' no está instalado. Algunas funciones de audio pueden ser limitadas o menos precisas.")

try:
    from scipy import signal
except ImportError:
    signal = None
    logging.warning("El módulo 'scipy' no está instalado. El remuestreo de audio será menos preciso.")

from whisper_app.utils import ffmpeg_utils
from whisper_app.core.exceptions import FFMpegError, FileProcessingError

logger = logging.getLogger(__name__)

def apply_vad(file_path: str, output_dir: str, ffmpeg_path: str = None) -> str | None:
    """
    Aplica Voice Activity Detection (VAD) usando FFMPEG.
    Lanza FFMpegError si FFMPEG falla o no se encuentra.
    Lanza FileNotFoundError si el archivo de entrada no existe.

    Args:
        file_path (str): Ruta al archivo de audio.
        output_dir (str): Directorio para guardar el archivo procesado.
        ffmpeg_path (str, optional): Ruta al ejecutable de FFMPEG. Defaults to None.

    Returns:
        str: Ruta al archivo procesado.

    Raises:
        FFMpegError: Si FFMPEG no se encuentra o falla la operación.
        FileNotFoundError: Si el archivo de entrada no existe.
    """
    if not ffmpeg_utils.check_ffmpeg(ffmpeg_path):
        msg = "FFMPEG no encontrado, no se puede aplicar VAD"
        logger.error(msg)
        raise FFMpegError(msg)

    if not os.path.exists(file_path):
        msg = f"El archivo no existe: {file_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    temp_file = None
    try:
        # Crear archivo temporal para salida
        temp_output = tempfile.NamedTemporaryFile(
            suffix='.wav',
            prefix='whisper_vad_',
            dir=output_dir,
            delete=False
        )
        temp_file = temp_output.name
        temp_output.close() # Cerrar el archivo para que FFMPEG pueda escribir

        # Aplicar filtro de silencio con FFMPEG
        command = [
            "ffmpeg",
            "-y",  # Sobrescribir sin preguntar
            "-i", file_path,
            "-af", f"silenceremove=stop_periods=-1:stop_duration=0.5:stop_threshold=0.5dB",
            "-ar", "16000",
            "-ac", "1",
            temp_file
        ]
        
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.decode()
            logger.error(f"Error al ejecutar VAD: {error_msg}")
            raise FFMpegError(f"Error al aplicar VAD con FFMPEG: {error_msg}")

        if not os.path.exists(temp_file) or os.path.getsize(temp_file) == 0:
            logger.warning(f"VAD no generó salida o el archivo está vacío: {temp_file}")
            raise FFMpegError(f"VAD no generó salida válida para {file_path}")

        logger.debug(f"VAD aplicado correctamente: {temp_file}")
        return temp_file

    except subprocess.SubprocessError as e:
        logger.error(f"Error de subprocess al aplicar VAD: {e}")
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError as rm_err:
                logger.warning(f"Error al eliminar archivo temporal: {rm_err}")
        raise FFMpegError(f"Error de subprocess al aplicar VAD: {e}") from e
    except Exception as e:
        logger.error(f"Error inesperado al aplicar VAD: {e}")
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError as rm_err:
                logger.warning(f"Error al eliminar archivo temporal: {rm_err}")
        raise FileProcessingError(f"Error inesperado al aplicar VAD: {e}") from e

def normalize_audio(file_path: str, output_dir: str, ffmpeg_path: str = None) -> str | None:
    """
    Normaliza el audio usando FFMPEG.
    Lanza FFMpegError si FFMPEG falla o no se encuentra.
    Lanza FileNotFoundError si el archivo de entrada no existe.

    Args:
        file_path (str): Ruta al archivo de audio.
        output_dir (str): Directorio para guardar el archivo normalizado.
        ffmpeg_path (str, optional): Ruta al ejecutable de FFMPEG. Defaults to None.

    Returns:
        str: Ruta al archivo normalizado.

    Raises:
        FFMpegError: Si FFMPEG no se encuentra o falla la operación.
        FileNotFoundError: Si el archivo de entrada no existe.
    """
    if not ffmpeg_utils.check_ffmpeg(ffmpeg_path):
        msg = "FFMPEG no encontrado, no se puede normalizar audio"
        logger.error(msg)
        raise FFMpegError(msg)

    if not os.path.exists(file_path):
        msg = f"El archivo no existe: {file_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    temp_file = None
    try:
        # Crear archivo temporal para salida
        temp_output = tempfile.NamedTemporaryFile(
            suffix='.wav',
            prefix='whisper_norm_',
            dir=output_dir,
            delete=False
        )
        temp_file = temp_output.name
        temp_output.close()

        # Normalizar audio con FFMPEG
        command = [
            "ffmpeg",
            "-y",  # Sobrescribir sin preguntar
            "-i", file_path,
            "-af", "loudnorm=I=-16:LRA=11:TP=-1.5",
            "-ar", "16000",
            "-ac", "1",
            temp_file
        ]
        
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.decode()
            logger.error(f"Error al normalizar audio: {error_msg}")
            if os.path.exists(temp_file):
                try: os.remove(temp_file)
                except OSError: pass
            raise FFMpegError(f"Error al normalizar audio con FFMPEG: {error_msg}")

        if not os.path.exists(temp_file) or os.path.getsize(temp_file) == 0:
            logger.error(f"Normalización no generó salida o el archivo está vacío: {temp_file}")
            raise FFMpegError(f"Normalización no generó salida válida para {file_path}")

        logger.debug(f"Audio normalizado correctamente: {temp_file}")
        return temp_file

    except subprocess.SubprocessError as e:
        logger.error(f"Error de subprocess al normalizar audio: {e}")
        if os.path.exists(temp_file):
            try: os.remove(temp_file)
            except OSError as rm_err: logger.warning(f"Error al eliminar temp: {rm_err}")
        raise FFMpegError(f"Error de subprocess al normalizar: {e}") from e
    except Exception as e:
        logger.error(f"Error inesperado al normalizar audio: {e}")
        if os.path.exists(temp_file):
            try: os.remove(temp_file)
            except OSError as rm_err: logger.warning(f"Error al eliminar temp: {rm_err}")
        raise FileProcessingError(f"Error inesperado al normalizar: {e}") from e

def load_audio(file_path: str, sample_rate: int = 16000) -> np.ndarray | None:
    """
    Carga un archivo de audio y lo convierte a la tasa de muestreo deseada.
    Utiliza FFMPEG para formatos no soportados directamente por soundfile.

    Args:
        file_path (str): Ruta al archivo de audio.
        sample_rate (int): Tasa de muestreo deseada (default: 16000 Hz).

    Returns:
        np.ndarray: Array con datos de audio o None si hay error.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        FileProcessingError: Si ocurre un error durante la carga o conversión.
        FFMpegError: Si FFMPEG es necesario y falla.
    """
    if not os.path.exists(file_path):
        msg = f"El archivo no existe: {file_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    temp_wav_file = None
    try:
        # Intentar cargar directamente con soundfile
        try:
            with sf.SoundFile(file_path, 'r') as f:
                audio = f.read(dtype='float32')
                sr = f.samplerate
                if sr != sample_rate:
                    audio = signal.resample(audio, int(len(audio) * sample_rate / sr))
                return audio
        except sf.SoundFileError:
            logger.debug(f"Soundfile no soporta {file_path}, intentando con FFMPEG")
            if not ffmpeg_utils.check_ffmpeg():
                raise FFMpegError("FFMPEG necesario para convertir formato no soportado por soundfile")

            with tempfile.NamedTemporaryFile(
                suffix='.wav',
                prefix='whisper_audio_',
                delete=False
            ) as temp_output:
                temp_wav_file = temp_output.name

            try:
                ffmpeg_utils.convert_to_wav(file_path, temp_wav_file, sample_rate=sample_rate)
                if not temp_wav_file or not os.path.exists(temp_wav_file):
                     raise FileProcessingError(f"No se pudo convertir a WAV: {file_path}")

                with sf.SoundFile(temp_wav_file, 'r') as f:
                    audio = f.read(dtype='float32')
                    sr = f.samplerate
                    if sr != sample_rate:
                        audio = signal.resample(audio, int(len(audio) * sample_rate / sr))
                    return audio
            except (FFMpegError, FileNotFoundError, sf.SoundFileError) as convert_err:
                 logger.error(f"Error al convertir/cargar con FFMPEG: {convert_err}")
                 raise FileProcessingError(f"Error procesando archivo con FFMPEG: {convert_err}") from convert_err

    except Exception as e:
        logger.error(f"Error al cargar audio: {e}")
        raise FileProcessingError(f"Error al cargar audio: {e}") from e
    finally:
        if temp_wav_file and os.path.exists(temp_wav_file):
            try:
                os.remove(temp_wav_file)
            except OSError as e:
                logger.warning(f"Error al eliminar archivo temporal {temp_wav_file}: {e}")

def save_audio(audio_data: np.ndarray, file_path: str, sample_rate: int = 16000):
    """
    Guarda datos de audio en un archivo.
    Utiliza FFMPEG para formatos no WAV.

    Args:
        audio_data (np.ndarray): Array numpy con los datos de audio.
        file_path (str): Ruta donde guardar el archivo.
        sample_rate (int): Tasa de muestreo (default: 16000 Hz).

    Raises:
        FileProcessingError: Si los datos de audio son inválidos o hay error al guardar.
        FFMpegError: Si FFMPEG es necesario y falla.
    """
    if audio_data is None or audio_data.size == 0:
        msg = "Array de audio vacío o None, no se puede guardar."
        logger.error(msg)
        raise FileProcessingError(msg)

    temp_wav_file = None
    try:
        file_ext = Path(file_path).suffix.lower()

        if file_ext == '.wav':
            if sf is not None:
                sf.write(file_path, audio_data, sample_rate)
            else:
                import wave
                with wave.open(file_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio_data.tobytes())
        else:
            if not ffmpeg_utils.check_ffmpeg():
                msg = "FFMPEG no encontrado, no se puede guardar en formato no-WAV"
                logger.error(msg)
                raise FFMpegError(msg)

            with tempfile.NamedTemporaryFile(
                suffix='.wav',
                prefix='whisper_audio_',
                delete=False
            ) as temp_output:
                temp_wav_file = temp_output.name

            if sf is not None:
                sf.write(temp_wav_file, audio_data, sample_rate)
            else:
                import wave
                with wave.open(temp_wav_file, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio_data.tobytes())

            command = [
                'ffmpeg',
                '-y',
                '-i', temp_wav_file,
                file_path
            ]
            result = subprocess.run(command, capture_output=True, check=False)

            if result.returncode != 0:
                error_msg = result.stderr.decode()
                logger.error(f"Error al convertir formato con FFMPEG: {error_msg}")
                raise FFMpegError(f"Error de FFMPEG al guardar en {file_ext}: {error_msg}")

            logger.debug(f"Audio guardado en {file_path} usando FFMPEG")

    except (sf.SoundFileError, subprocess.SubprocessError, FFMpegError) as e:
        logger.error(f"Error al guardar audio: {e}")
        raise FileProcessingError(f"Error al guardar audio en {file_path}: {e}") from e
    except Exception as e:
        logger.error(f"Error inesperado al guardar audio: {e}")
        raise FileProcessingError(f"Error inesperado al guardar audio: {e}") from e
    finally:
        if temp_wav_file and os.path.exists(temp_wav_file):
            try:
                os.remove(temp_wav_file)
            except OSError as e:
                logger.warning(f"Error al eliminar archivo temporal {temp_wav_file}: {e}")

def detect_voice_segments(audio_array, sample_rate=16000, threshold=0.01, min_silence=0.5):
    """
    Detecta segmentos con voz en un array de audio
    
    Args:
        audio_array (np.ndarray): Array con datos de audio
        sample_rate (int): Frecuencia de muestreo
        threshold (float): Umbral de energía para detectar voz
        min_silence (float): Duración mínima de silencio en segundos
    
    Returns:
        list: Lista de tuplas (inicio, fin) en segundos
    """
    if audio_array is None or len(audio_array) == 0:
        logger.error("Array de audio vacío o None")
        return []
    
    try:
        # Calcular energía del audio
        energy = np.abs(audio_array)
        
        # Suavizar energía
        window_size = int(0.02 * sample_rate)  # Ventana de 20ms
        if window_size > 1:
            kernel = np.ones(window_size) / window_size
            energy = np.convolve(energy, kernel, mode='same')
        
        # Detectar segmentos por encima del umbral
        is_speech = energy > threshold
        
        # Convertir a segmentos
        min_silence_samples = int(min_silence * sample_rate)
        segments = []
        in_speech = False
        start = 0
        
        for i, speech in enumerate(is_speech):
            if not in_speech and speech:
                # Inicio de segmento de voz
                in_speech = True
                start = i
            elif in_speech and not speech:
                # Fin de segmento de voz
                # Verificar que el silencio dure lo suficiente
                j = i
                while j < len(is_speech) and not is_speech[j]:
                    j += 1
                    if j - i >= min_silence_samples:
                        # Si hay suficiente silencio, terminar segmento
                        in_speech = False
                        segments.append((start / sample_rate, i / sample_rate))
                        break
                
                # Si llegamos al final sin terminar el segmento
                if j >= len(is_speech) and in_speech:
                    in_speech = False
                    segments.append((start / sample_rate, i / sample_rate))
        
        # Si terminamos en voz, agregar último segmento
        if in_speech:
            segments.append((start / sample_rate, len(audio_array) / sample_rate))
        
        return segments
    
    except Exception as e:
        logger.error(f"Error al detectar segmentos de voz: {e}")
        return []