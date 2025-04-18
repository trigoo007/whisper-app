#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo core de WhisperApp

Contiene los componentes fundamentales para la funcionalidad principal:
- Transcribir audio/video
- Grabar desde micrófono
- Gestionar archivos
- Gestionar configuración
"""

from whisper_app.core.config_manager import ConfigManager
from whisper_app.core.transcriber import Transcriber
from whisper_app.core.recorder import AudioRecorder
from whisper_app.core.file_manager import FileManager
from whisper_app.core.realtime_transcriber import RealtimeTranscriber
from whisper_app.core.exceptions import (
    WhisperAppError, ConfigError, FFMpegError, ModelLoadError, TranscriptionError, RecordingError, FileProcessingError
)