class WhisperAppError(Exception):
    """Excepción base para errores de WhisperApp."""
    pass

class ConfigError(WhisperAppError):
    """Error relacionado con la configuración."""
    pass

class FFMpegError(WhisperAppError):
    """Error relacionado con FFMPEG o ffprobe."""
    pass

class ModelLoadError(WhisperAppError):
    """Error al cargar o descargar un modelo Whisper."""
    pass

class TranscriptionError(WhisperAppError):
    """Error durante el proceso de transcripción."""
    pass

class RecordingError(WhisperAppError):
    """Error durante la grabación de audio."""
    pass

class FileProcessingError(WhisperAppError):
    """Error al procesar/importar/exportar un archivo."""
    pass 