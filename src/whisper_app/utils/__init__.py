#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo utils de WhisperApp

Contiene utilidades auxiliares para:
- Interactuar con FFMPEG
- Procesar audio
- Formatear texto y subtítulos
"""

from whisper_app.utils.ffmpeg_utils import (
    verify_ffmpeg,
    find_ffmpeg,
    get_file_info,
    get_file_duration,
    convert_to_wav,
    extract_audio,
    segment_audio
)

from whisper_app.utils.audio_utils import (
    apply_vad,
    normalize_audio,
    load_audio,
    save_audio,
    detect_voice_segments
)

from whisper_app.utils.text_utils import (
    save_txt,
    save_srt,
    save_vtt,
    format_timestamp_srt,
    format_timestamp_vtt,
    clean_text,
    merge_segments,
    detect_speakers,
    split_long_segments,
    extract_keywords
)