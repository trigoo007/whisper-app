#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidades para formateo de texto y subtítulos en WhisperApp
"""

import os
import logging
import re

# Importamos la función para obtener stopwords desde el nuevo módulo
from whisper_app.utils.language_data import get_stopwords

logger = logging.getLogger(__name__)

def save_txt(transcription, file_path):
    """
    Guarda transcripción en formato de texto plano (TXT)
    
    Args:
        transcription (dict): Resultado de transcripción de Whisper
        file_path (str): Ruta donde guardar el archivo
    
    Returns:
        str: Ruta al archivo guardado o None si hay error
    """
    try:
        # Asegurar que existe el directorio
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(transcription["text"].strip())
        
        logger.info(f"Transcripción guardada como TXT: {file_path}")
        return file_path
    
    except Exception as e:
        logger.error(f"Error al guardar TXT: {e}")
        return None

def save_srt(transcription, file_path):
    """
    Guarda transcripción en formato de subtítulos SRT
    
    Args:
        transcription (dict): Resultado de transcripción de Whisper
        file_path (str): Ruta donde guardar el archivo
    
    Returns:
        str: Ruta al archivo guardado o None si hay error
    """
    try:
        # Asegurar que existe el directorio
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(transcription["segments"]):
                # Formatear inicio y fin en formato SRT (HH:MM:SS,mmm)
                start = format_timestamp_srt(segment['start'])
                end = format_timestamp_srt(segment['end'])
                
                # Escribir entrada SRT
                f.write(f"{i+1}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{segment['text'].strip()}\n\n")
        
        logger.info(f"Transcripción guardada como SRT: {file_path}")
        return file_path
    
    except Exception as e:
        logger.error(f"Error al guardar SRT: {e}")
        return None

def save_vtt(transcription, file_path):
    """
    Guarda transcripción en formato de subtítulos WebVTT
    
    Args:
        transcription (dict): Resultado de transcripción de Whisper
        file_path (str): Ruta donde guardar el archivo
    
    Returns:
        str: Ruta al archivo guardado o None si hay error
    """
    try:
        # Asegurar que existe el directorio
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            
            for segment in transcription["segments"]:
                # Formatear inicio y fin en formato VTT (HH:MM:SS.mmm)
                start = format_timestamp_vtt(segment['start'])
                end = format_timestamp_vtt(segment['end'])
                
                # Escribir entrada VTT
                f.write(f"{start} --> {end}\n")
                f.write(f"{segment['text'].strip()}\n\n")
        
        logger.info(f"Transcripción guardada como VTT: {file_path}")
        return file_path
    
    except Exception as e:
        logger.error(f"Error al guardar VTT: {e}")
        return None

def format_timestamp_srt(seconds):
    """
    Formatea segundos en formato SRT (HH:MM:SS,mmm)
    
    Args:
        seconds (float): Tiempo en segundos
    
    Returns:
        str: Tiempo formateado
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

def format_timestamp_vtt(seconds):
    """
    Formatea segundos en formato WebVTT (HH:MM:SS.mmm)
    
    Args:
        seconds (float): Tiempo en segundos
    
    Returns:
        str: Tiempo formateado
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"

def clean_text(text):
    """
    Limpia y normaliza texto de transcripción
    
    Args:
        text (str): Texto a limpiar
    
    Returns:
        str: Texto limpio
    """
    if not text:
        return ""
    
    # Eliminar espacios en blanco múltiples
    text = re.sub(r'\s+', ' ', text)
    
    # Eliminar espacios antes de puntuación
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    
    # Corregir espacios después de puntuación
    text = re.sub(r'([.,;:!?])([A-Za-z0-9])', r'\1 \2', text)
    
    # Asegurar mayúscula al inicio de oración
    text = re.sub(r'([.!?])\s+([a-z])', lambda m: m.group(1) + ' ' + m.group(2).upper(), text)
    
    # Asegurar que la primera letra sea mayúscula
    if text and text[0].isalpha() and text[0].islower():
        text = text[0].upper() + text[1:]
    
    return text.strip()

def merge_segments(segments, max_chars=120, max_duration=5.0):
    """
    Combina segmentos cortos para subtítulos más legibles
    
    Args:
        segments (list): Lista de segmentos de Whisper
        max_chars (int): Número máximo de caracteres por segmento
        max_duration (float): Duración máxima por segmento en segundos
    
    Returns:
        list: Lista de segmentos combinados
    """
    if not segments:
        return []
    
    merged = []
    current = None
    
    for segment in segments:
        if current is None:
            # Primer segmento
            current = segment.copy()
            continue
        
        # Verificar si se puede combinar
        combined_text = current['text'] + ' ' + segment['text']
        combined_duration = segment['end'] - current['start']
        
        if (len(combined_text) <= max_chars and
            combined_duration <= max_duration and
            segment['start'] - current['end'] < 0.5):  # Menos de 0.5s de separación
            
            # Combinar segmentos
            current['text'] = combined_text
            current['end'] = segment['end']
        else:
            # No se puede combinar, guardar actual e iniciar nuevo
            merged.append(current)
            current = segment.copy()
    
    # Agregar último segmento
    if current is not None:
        merged.append(current)
    
    return merged

def label_segments_by_pause(segments, num_speakers=2):
    """
    Asigna etiquetas de hablante basándose únicamente en pausas entre segmentos.
    
    IMPORTANTE: Esta NO es una verdadera diarización. Es sólo una aproximación
    heurística basada en pausas que puede ser útil para visualización básica.
    Para diarización real, se recomienda utilizar bibliotecas especializadas
    como pyannote.audio.

    Args:
        segments (list): Lista de segmentos de Whisper
        num_speakers (int): Número estimado de hablantes

    Returns:
        list: Segmentos con etiquetas de hablante simples
    """
    if not segments:
        return []
    
    # Copia para no modificar original
    result = []
    
    # Inicializar con primer hablante
    current_speaker = 0
    last_end = 0
    
    for segment in segments:
        # Copiar segmento
        new_segment = segment.copy()
        
        # Decidir si cambiar de hablante basado en pausas
        gap = segment['start'] - last_end
        if gap > 1.5:  # Pausa larga sugiere cambio de hablante
            current_speaker = (current_speaker + 1) % num_speakers
        
        # Etiquetar hablante
        new_segment['speaker'] = f"Speaker {current_speaker + 1}"
        
        # Actualizar último tiempo
        last_end = segment['end']
        
        result.append(new_segment)
    
    return result

# Mantener el alias por compatibilidad, pero marcar como obsoleto
detect_speakers = label_segments_by_pause  # OBSOLETO: Usar label_segments_by_pause

def split_long_segments(segments, max_chars=120, max_duration=5.0):
    """
    Divide segmentos largos para subtítulos más legibles
    
    Args:
        segments (list): Lista de segmentos de Whisper
        max_chars (int): Número máximo de caracteres por segmento
        max_duration (float): Duración máxima por segmento en segundos
    
    Returns:
        list: Lista de segmentos divididos
    """
    if not segments:
        return []
    
    result = []
    
    for segment in segments:
        # Verificar si el segmento es corto
        if (len(segment['text']) <= max_chars and
            segment['end'] - segment['start'] <= max_duration):
            # Mantener segmento sin cambios
            result.append(segment.copy())
            continue
        
        # Dividir texto en frases
        text = segment['text']
        duration = segment['end'] - segment['start']
        
        # Buscar puntos naturales de división (puntuación)
        potential_splits = []
        for match in re.finditer(r'[.!?]\s+', text):
            potential_splits.append(match.end())
        
        # Si no hay puntos de división o si es muy corto, dividir por longitud
        if not potential_splits or len(potential_splits) == 1:
            words = text.split()
            chunks = []
            current_chunk = []
            current_length = 0
            
            for word in words:
                # +1 por el espacio
                if current_length + len(word) + 1 > max_chars and current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = [word]
                    current_length = len(word)
                else:
                    current_chunk.append(word)
                    current_length += len(word) + 1
            
            # Agregar último chunk si queda algo
            if current_chunk:
                chunks.append(' '.join(current_chunk))
        else:
            # Dividir por puntuación
            chunks = []
            last_end = 0
            
            for split_point in potential_splits:
                if split_point - last_end > max_chars:
                    # Si el segmento es muy largo, dividir por palabras
                    sub_text = text[last_end:split_point]
                    words = sub_text.split()
                    sub_chunks = []
                    current_chunk = []
                    current_length = 0
                    
                    for word in words:
                        if current_length + len(word) + 1 > max_chars and current_chunk:
                            sub_chunks.append(' '.join(current_chunk))
                            current_chunk = [word]
                            current_length = len(word)
                        else:
                            current_chunk.append(word)
                            current_length += len(word) + 1
                    
                    if current_chunk:
                        sub_chunks.append(' '.join(current_chunk))
                    
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(text[last_end:split_point].strip())
                
                last_end = split_point
            
            # Último segmento
            if last_end < len(text):
                chunks.append(text[last_end:].strip())
        
        # Crear nuevos segmentos
        chunk_duration = duration / len(chunks)
        for i, chunk in enumerate(chunks):
            start_time = segment['start'] + i * chunk_duration
            end_time = segment['start'] + (i + 1) * chunk_duration
            
            result.append({
                'id': segment['id'],  # Mantener ID original
                'start': start_time,
                'end': end_time,
                'text': chunk.strip()
            })
    
    return result

def extract_keywords(text, max_keywords=5, language='es'):
    """
    Extrae palabras clave de un texto
    Método simple basado en frecuencia de palabras
    
    Args:
        text (str): Texto de la transcripción
        max_keywords (int): Número máximo de palabras clave
        language (str): Código de idioma para stopwords
    
    Returns:
        list: Lista de palabras clave
    """
    if not text:
        return []
    
    # Convertir a minúsculas
    text = text.lower()
    
    # Eliminar puntuación
    text = re.sub(r'[^\w\s]', '', text)
    
    # Dividir en palabras
    words = text.split()
    
    # Eliminar palabras vacías (stopwords)
    stopwords = get_stopwords(language)
    
    filtered_words = [word for word in words if word not in stopwords and len(word) > 3]
    
    # Contar frecuencia
    word_count = {}
    for word in filtered_words:
        word_count[word] = word_count.get(word, 0) + 1
    
    # Ordenar por frecuencia
    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    
    # Tomar las N palabras más frecuentes
    return [word for word, _ in sorted_words[:max_keywords]]