#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidades para interactuar con FFMPEG en WhisperApp
"""

import os
import sys
import logging
import subprocess
import shutil
from pathlib import Path
import json
import tempfile

from whisper_app.core.exceptions import FFMpegError # Importar la excepción personalizada

logger = logging.getLogger(__name__)

def verify_ffmpeg():
    """
    Verifica si FFMPEG está disponible en el sistema
    
    Returns:
        bool: True si FFMPEG está disponible, False si no
    """
    try:
        # Intentar ejecutar ffmpeg -version para obtener información detallada
        result = subprocess.run(["ffmpeg", "-version"], 
                               capture_output=True, 
                               text=True, 
                               check=True)
        version_info = result.stdout.split('\n')[0]
        logger.info(f"FFMPEG encontrado: {version_info}")
        return True
    except subprocess.SubprocessError as e:
        logger.debug(f"Error al verificar FFMPEG: {e}")
    except FileNotFoundError as e:
        logger.debug(f"Error al verificar FFMPEG en ruta específica: {e}")
    
    logger.warning("FFMPEG no encontrado en el sistema")
    return False

def find_ffmpeg():
    """
    Intenta encontrar la ruta de FFMPEG en el sistema
    
    Returns:
        str: Ruta a FFMPEG o una cadena vacía si no se encuentra
    """
    # Primero buscar en PATH
    ffmpeg_command = "ffmpeg.exe" if os.name == 'nt' else "ffmpeg"
    
    try:
        # Buscar en PATH
        ffmpeg_path = shutil.which(ffmpeg_command)
        if ffmpeg_path:
            return ffmpeg_path
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.debug(f"Error buscando FFMPEG en PATH: {e}")
    
    # Verificar ubicaciones comunes según sistema operativo
    common_locations = []
    
    if os.name == 'nt':  # Windows
        program_files = os.environ.get('ProgramFiles', r'C:\Program Files')
        program_files_x86 = os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')
        
        common_locations = [
            os.path.join(program_files, 'ffmpeg', 'bin', 'ffmpeg.exe'),
            os.path.join(program_files_x86, 'ffmpeg', 'bin', 'ffmpeg.exe'),
            r'C:\ffmpeg\bin\ffmpeg.exe'
        ]
    elif sys.platform == 'darwin':  # macOS
        common_locations = [
            '/usr/local/bin/ffmpeg',
            '/opt/homebrew/bin/ffmpeg',
            '/opt/local/bin/ffmpeg'
        ]
    else:  # Linux y otros
        common_locations = [
            '/usr/bin/ffmpeg',
            '/usr/local/bin/ffmpeg',
            '/opt/ffmpeg/bin/ffmpeg'
        ]
    
    # Verificar cada ubicación
    for location in common_locations:
        if os.path.exists(location) and os.access(location, os.X_OK):
            return location
    
    # No se encontró FFMPEG
    return ""

def verify_ffprobe():
    """
    Verifica si ffprobe está disponible en el sistema
    Returns:
        bool: True si ffprobe está disponible, False si no
    """
    try:
        subprocess.run(
            ["ffprobe", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        logger.debug("ffprobe verificado correctamente")
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning("ffprobe no encontrado en el sistema")
        return False

def verify_ffmpeg_components():
    """
    Verifica que tanto ffmpeg como ffprobe estén disponibles
    Returns:
        bool: True si ambos están disponibles, False si no
    """
    return verify_ffmpeg() and verify_ffprobe()

def get_file_info(file_path):
    """
    Obtiene información de un archivo multimedia usando FFMPEG
    
    Args:
        file_path (str): Ruta al archivo multimedia
    
    Returns:
        dict: Información del archivo o None si hay error
    """
    if not verify_ffmpeg_components():
        logger.error("FFMPEG o ffprobe no encontrados, no se puede obtener información del archivo")
        return None
    
    if not os.path.exists(file_path):
        logger.error(f"El archivo no existe: {file_path}")
        return None
    
    try:
        # Usar ffprobe para obtener información
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            stderr_output = result.stderr.decode()
            logger.error(f"Error al ejecutar ffprobe: {stderr_output}")
            return None
        
        # Parsear salida JSON
        info = json.loads(result.stdout)
        
        # Extraer información relevante
        output = {
            "format": info.get("format", {}).get("format_name", "unknown"),
            "duration": float(info.get("format", {}).get("duration", 0)),
            "bitrate": int(info.get("format", {}).get("bit_rate", 0)),
            "streams": []
        }
        
        # Procesar streams
        for stream in info.get("streams", []):
            stream_info = {
                "index": stream.get("index"),
                "codec_type": stream.get("codec_type"),
                "codec_name": stream.get("codec_name"),
            }
            
            # Información específica para audio
            if stream.get("codec_type") == "audio":
                stream_info.update({
                    "channels": stream.get("channels"),
                    "sample_rate": stream.get("sample_rate"),
                    "bit_rate": stream.get("bit_rate")
                })
            # Información específica para video
            elif stream.get("codec_type") == "video":
                stream_info.update({
                    "width": stream.get("width"),
                    "height": stream.get("height"),
                    "frame_rate": parse_frame_rate(stream.get("r_frame_rate", "0/1"))
                })
            
            output["streams"].append(stream_info)
        
        return output
    
    except (json.JSONDecodeError, KeyError, IndexError, subprocess.SubprocessError, FileNotFoundError) as e:
        logger.error(f"Error al obtener información del archivo: {e}")
        return None

def parse_frame_rate(rate_str):
    """
    Parsea una cadena de velocidad de fotogramas (ej: "30000/1001") de forma segura
    
    Args:
        rate_str (str): Cadena con formato de fracción
    
    Returns:
        float: Velocidad de fotogramas
    """
    try:
        if "/" in rate_str:
            numerator, denominator = rate_str.split("/")
            return float(numerator) / float(denominator)
        else:
            return float(rate_str)
    except (ValueError, ZeroDivisionError):
        return 0.0

def get_file_duration(file_path):
    """
    Obtiene la duración de un archivo multimedia
    
    Args:
        file_path (str): Ruta al archivo
    
    Returns:
        float: Duración en segundos o None si hay error
    """
    if not verify_ffmpeg():
        logger.error("FFMPEG no encontrado, no se puede obtener duración")
        return None
    
    if not os.path.exists(file_path):
        logger.error(f"El archivo no existe: {file_path}")
        return None
    
    try:
        # Usar ffprobe para obtener duración
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            stderr_output = result.stderr.decode()
            logger.error(f"Error al ejecutar ffprobe: {stderr_output}")
            return None
        
        # Parsear salida
        duration = float(result.stdout.strip())
        return duration
    
    except (subprocess.SubprocessError, FileNotFoundError, ValueError, KeyError) as e:
        logger.error(f"Error al obtener duración: {e}")
        return None

def convert_to_wav(input_path, output_path, sample_rate=16000, channels=1, normalize=False):
    """
    Convierte un archivo multimedia a formato WAV
    
    Args:
        input_path (str): Ruta al archivo de entrada
        output_path (str): Ruta al archivo de salida
        sample_rate (int): Frecuencia de muestreo en Hz
        channels (int): Número de canales
        normalize (bool): Si se debe normalizar el audio
    
    Returns:
        str: Ruta al archivo convertido o None si hay error
    """
    if not verify_ffmpeg():
        logger.error("FFMPEG no encontrado, no se puede convertir")
        return None
    
    if not os.path.exists(input_path):
        logger.error(f"El archivo no existe: {input_path}")
        return None
    
    try:
        # Construir comando FFMPEG
        command = [
            "ffmpeg",
            "-y",  # Sobrescribir sin preguntar
            "-i", input_path,
            "-ar", str(sample_rate),
            "-ac", str(channels),
            "-c:a", "pcm_s16le"  # PCM 16-bit little-endian
        ]
        
        # Agregar normalización si se solicita
        if normalize:
            command.extend([
                "-af", "loudnorm=I=-16:LRA=11:TP=-1.5"
            ])
        
        command.append(output_path)
        
        # Ejecutar comando
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.decode()
            logger.error(f"Error al ejecutar FFMPEG: {error_msg}")
            # Capturar y propagar el mensaje de error específico
            raise FFMpegError(f"Error de FFMPEG: {error_msg}")
        
        if not os.path.exists(output_path):
            logger.error(f"No se generó el archivo de salida: {output_path}")
            return None
        
        return output_path
    except subprocess.SubprocessError as e:
        # Capturar otros errores de subprocess
        logger.error(f"Error de subprocess durante la conversión: {e}")
        raise FFMpegError(f"Error de subprocess durante la conversión: {e}") from e
    except Exception as e:
        logger.error(f"Error al convertir archivo: {e}")
        return None

def extract_audio(input_path, output_path, start_time=None, duration=None):
    """
    Extrae audio de un archivo multimedia
    
    Args:
        input_path (str): Ruta al archivo de entrada
        output_path (str): Ruta al archivo de salida
        start_time (float): Tiempo de inicio en segundos
        duration (float): Duración en segundos
    
    Returns:
        str: Ruta al archivo extraído o None si hay error
    """
    if not verify_ffmpeg():
        logger.error("FFMPEG no encontrado, no se puede extraer audio")
        return None
    
    if not os.path.exists(input_path):
        logger.error(f"El archivo no existe: {input_path}")
        return None
    
    try:
        # Construir comando FFMPEG
        command = [
            "ffmpeg",
            "-y"  # Sobrescribir sin preguntar
        ]
        
        # Agregar tiempo de inicio si se especifica
        if start_time is not None:
            command.extend(["-ss", str(start_time)])
        
        command.extend(["-i", input_path])
        
        # Agregar duración si se especifica
        if duration is not None:
            command.extend(["-t", str(duration)])
        
        # Configurar salida de audio
        command.extend([
            "-vn",  # Sin video
            "-c:a", "copy",  # Copiar audio sin recodificar
            output_path
        ])
        
        # Ejecutar comando
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if result.returncode != 0:
            logger.error(f"Error al ejecutar FFMPEG: {result.stderr.decode()}")
            return None
        
        if not os.path.exists(output_path):
            logger.error(f"No se generó el archivo de salida: {output_path}")
            return None
        
        return output_path
    
    except Exception as e:
        logger.error(f"Error al extraer audio: {e}")
        return None

def segment_audio(input_path, output_pattern, segment_duration=600):
    """
    Divide un archivo de audio en segmentos
    
    Args:
        input_path (str): Ruta al archivo de entrada
        output_pattern (str): Patrón para archivos de salida (ej: "segment_%03d.wav")
        segment_duration (int): Duración de cada segmento en segundos
    
    Returns:
        list: Lista de rutas a los segmentos creados o None si hay error
    """
    if not verify_ffmpeg():
        logger.error("FFMPEG no encontrado, no se puede segmentar audio")
        return None
    
    if not os.path.exists(input_path):
        logger.error(f"El archivo no existe: {input_path}")
        return None
    
    try:
        # Crear directorio de salida si no existe
        output_dir = os.path.dirname(output_pattern)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Construir comando FFMPEG
        command = [
            "ffmpeg",
            "-y",  # Sobrescribir sin preguntar
            "-i", input_path,
            "-f", "segment",
            "-segment_time", str(segment_duration),
            "-c", "copy",
            output_pattern
        ]
        
        # Ejecutar comando
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if result.returncode != 0:
            logger.error(f"Error al ejecutar FFMPEG: {result.stderr.decode()}")
            return None
        
        # Buscar segmentos generados
        segments = []
        base_dir = os.path.dirname(output_pattern)
        base_name = os.path.basename(output_pattern)
        
        # Reemplazar formato de segmento por regex para búsqueda
        import re
        search_pattern = re.sub(r'%\d*d', r'\d+', base_name)
        search_pattern = f"^{search_pattern}$".replace(".", r"\.")
        
        for file in os.listdir(base_dir):
            if re.match(search_pattern, file):
                segments.append(os.path.join(base_dir, file))
        
        # Ordenar segmentos
        segments.sort()
        
        return segments
    
    except Exception as e:
        logger.error(f"Error al segmentar audio: {e}")
        return None