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

from whisper_app.utils.ffmpeg_utils import verify_ffmpeg, convert_to_wav

logger = logging.getLogger(__name__)

def apply_vad(file_path):
    """
    Aplica detección de actividad de voz (VAD) para filtrar silencio
    
    Args:
        file_path (str): Ruta al archivo de audio
    
    Returns:
        str: Ruta al archivo procesado o None si hay error
    """
    if not verify_ffmpeg():
        logger.error("FFMPEG no encontrado, no se puede aplicar VAD")
        return file_path
    
    if not os.path.exists(file_path):
        logger.error(f"El archivo no existe: {file_path}")
        return file_path
    
    try:
        # Crear archivo temporal para salida
        output_file = tempfile.NamedTemporaryFile(
            suffix='.wav',
            prefix='whisper_vad_',
            delete=False
        ).name
        
        # Aplicar filtro de silencio con FFMPEG
        command = [
            "ffmpeg",
            "-y",  # Sobrescribir sin preguntar
            "-i", file_path,
            "-af", "silenceremove=stop_periods=-1:stop_duration=1:stop_threshold=-50dB",
            "-ar", "16000",
            "-ac", "1",
            output_file
        ]
        
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if result.returncode != 0:
            logger.error(f"Error al ejecutar VAD: {result.stderr.decode()}")
            return file_path
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            logger.debug(f"VAD aplicado correctamente: {output_file}")
            return output_file
        else:
            logger.warning("El archivo de salida de VAD está vacío o no se creó")
            return file_path
        
    except Exception as e:
        logger.error(f"Error al aplicar VAD: {e}")
        return file_path

def normalize_audio(file_path):
    """
    Normaliza volumen de audio
    
    Args:
        file_path (str): Ruta al archivo de audio
    
    Returns:
        str: Ruta al archivo normalizado o None si hay error
    """
    if not verify_ffmpeg():
        logger.error("FFMPEG no encontrado, no se puede normalizar audio")
        return file_path
    
    if not os.path.exists(file_path):
        logger.error(f"El archivo no existe: {file_path}")
        return file_path
    
    try:
        # Crear archivo temporal para salida
        output_file = tempfile.NamedTemporaryFile(
            suffix='.wav',
            prefix='whisper_norm_',
            delete=False
        ).name
        
        # Normalizar audio con FFMPEG
        command = [
            "ffmpeg",
            "-y",  # Sobrescribir sin preguntar
            "-i", file_path,
            "-af", "loudnorm=I=-16:LRA=11:TP=-1.5",
            "-ar", "16000",
            "-ac", "1",
            output_file
        ]
        
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if result.returncode != 0:
            logger.error(f"Error al normalizar audio: {result.stderr.decode()}")
            return file_path
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            logger.debug(f"Audio normalizado correctamente: {output_file}")
            return output_file
        else:
            logger.warning("El archivo de salida normalizado está vacío o no se creó")
            return file_path
        
    except Exception as e:
        logger.error(f"Error al normalizar audio: {e}")
        return file_path

def load_audio(file_path, sample_rate=16000):
    """
    Carga un archivo de audio en un array NumPy
    
    Args:
        file_path (str): Ruta al archivo de audio
        sample_rate (int): Frecuencia de muestreo deseada
    
    Returns:
        np.ndarray: Array con datos de audio o None si hay error
    """
    if not os.path.exists(file_path):
        logger.error(f"El archivo no existe: {file_path}")
        return None
    
    try:
        # Primero convertir a WAV si es necesario
        temp_wav = None
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext != '.wav':
            temp_wav = tempfile.NamedTemporaryFile(
                suffix='.wav',
                prefix='whisper_audio_',
                delete=False
            ).name
            
            if not convert_to_wav(file_path, temp_wav, sample_rate=sample_rate, channels=1):
                logger.error(f"No se pudo convertir a WAV: {file_path}")
                return None
            
            file_path = temp_wav
        
        # Cargar archivo WAV
        try:
            import soundfile as sf
            audio, sr = sf.read(file_path)
            
            # Convertir a mono si es estéreo
            if len(audio.shape) > 1 and audio.shape[1] > 1:
                audio = audio.mean(axis=1)
            
            # Resamplear si es necesario
            if sr != sample_rate:
                try:
                    from scipy import signal
                    audio = signal.resample(audio, int(len(audio) * sample_rate / sr))
                except ImportError:
                    logger.warning("No se pudo importar scipy para resamplear audio")
            
            # Limpiar archivo temporal
            if temp_wav and os.path.exists(temp_wav):
                try:
                    os.unlink(temp_wav)
                except:
                    pass
            
            return audio
            
        except ImportError:
            logger.warning("No se pudo importar soundfile, intentando con wave")
            
            # Alternativa usando wave
            import wave
            import numpy as np
            
            with wave.open(file_path, 'rb') as wf:
                n_frames = wf.getnframes()
                audio = np.frombuffer(wf.readframes(n_frames), dtype=np.int16)
                audio = audio.astype(np.float32) / 32768.0  # Normalizar a [-1.0, 1.0]
                
                # Convertir a mono si es estéreo
                if wf.getnchannels() > 1:
                    audio = audio.reshape(-1, wf.getnchannels()).mean(axis=1)
                
                # Resamplear si es necesario
                sr = wf.getframerate()
                if sr != sample_rate:
                    try:
                        from scipy import signal
                        audio = signal.resample(audio, int(len(audio) * sample_rate / sr))
                    except ImportError:
                        logger.warning("No se pudo importar scipy para resamplear audio")
                
                # Limpiar archivo temporal
                if temp_wav and os.path.exists(temp_wav):
                    try:
                        os.unlink(temp_wav)
                    except:
                        pass
                
                return audio
    
    except Exception as e:
        logger.error(f"Error al cargar audio: {e}")
        
        # Limpiar archivo temporal en caso de error
        if temp_wav and os.path.exists(temp_wav):
            try:
                os.unlink(temp_wav)
            except:
                pass
        
        return None

def save_audio(audio_array, file_path, sample_rate=16000):
    """
    Guarda un array NumPy como archivo de audio
    
    Args:
        audio_array (np.ndarray): Array con datos de audio
        file_path (str): Ruta donde guardar el archivo
        sample_rate (int): Frecuencia de muestreo
    
    Returns:
        bool: True si se guardó correctamente, False en caso contrario
    """
    if audio_array is None or len(audio_array) == 0:
        logger.error("Array de audio vacío o None")
        return False
    
    try:
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        # Determinar formato según extensión
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Normalizar audio si es necesario
        if audio_array.dtype != np.int16:
            if audio_array.max() <= 1.0 and audio_array.min() >= -1.0:
                # Convertir de float [-1.0, 1.0] a int16
                audio_array = (audio_array * 32767).astype(np.int16)
            elif audio_array.dtype == np.float32 or audio_array.dtype == np.float64:
                # Normalizar y convertir a int16
                max_val = max(abs(audio_array.max()), abs(audio_array.min()))
                if max_val > 0:
                    audio_array = (audio_array / max_val * 32767).astype(np.int16)
                else:
                    audio_array = audio_array.astype(np.int16)
        
        # Guardar según formato
        if file_ext == '.wav':
            try:
                import soundfile as sf
                sf.write(file_path, audio_array, sample_rate)
                return True
            except ImportError:
                logger.warning("No se pudo importar soundfile, intentando con wave")
                
                import wave
                import struct
                
                with wave.open(file_path, 'wb') as wf:
                    wf.setnchannels(1)  # Mono
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(sample_rate)
                    
                    # Convertir a bytes
                    audio_bytes = audio_array.tobytes()
                    wf.writeframes(audio_bytes)
                
                return True
        else:
            # Para otros formatos, usar FFMPEG
            if not verify_ffmpeg():
                logger.error("FFMPEG no encontrado, no se puede guardar en formato no-WAV")
                return False
            
            # Guardar primero como WAV temporal
            temp_wav = tempfile.NamedTemporaryFile(
                suffix='.wav',
                prefix='whisper_audio_',
                delete=False
            ).name
            
            try:
                import soundfile as sf
                sf.write(temp_wav, audio_array, sample_rate)
            except ImportError:
                # Alternativa con wave
                import wave
                with wave.open(temp_wav, 'wb') as wf:
                    wf.setnchannels(1)  # Mono
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio_array.tobytes())
            
            # Convertir a formato deseado con FFMPEG
            command = [
                "ffmpeg",
                "-y",  # Sobrescribir sin preguntar
                "-i", temp_wav,
                file_path
            ]
            
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Limpiar archivo temporal
            if os.path.exists(temp_wav):
                try:
                    os.unlink(temp_wav)
                except:
                    pass
            
            if result.returncode != 0:
                logger.error(f"Error al convertir formato: {result.stderr.decode()}")
                return False
            
            return os.path.exists(file_path)
    
    except Exception as e:
        logger.error(f"Error al guardar audio: {e}")
        return False

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