# WhisperApp - Transcripción de Audio y Video

Una aplicación de escritorio robusta para transcribir archivos de audio y video utilizando OpenAI Whisper. Convierte voz a texto con facilidad, con soporte para múltiples idiomas, traducción, exportación de subtítulos y más.

![WhisperApp Screenshot](docs/screenshot.png)

## Características principales

- 🔊 **Transcripción de voz a texto** usando Whisper de OpenAI
- 🎤 **Grabación de audio** directamente desde el micrófono
- 🌐 **Detección automática de idioma** y soporte para transcripción en múltiples idiomas
- 🔄 **Traducción** a diferentes idiomas
- 📝 **Exportación** en formatos TXT, SRT y WebVTT
- 🎞️ **Soporte para múltiples formatos** de audio y video
- 🔍 **Interfaz intuitiva** para gestionar archivos y resultados
- ⚙️ **Opciones avanzadas** para usuarios experimentados

## Requisitos previos

- Python 3.7 o superior
- FFmpeg instalado en el sistema

## Instalación

### Opción 1: Instalación desde PyPI

```bash
pip install whisper-app
```

### Opción 2: Instalación desde el código fuente

```bash
git clone https://github.com/trigoo007/whisper-app
cd whisper-app
pip install -e .
```

### Opción 3: Instalación con pipx (recomendado para usuarios finales)

```bash
pipx install whisper-app
```

## Uso

### Iniciar la aplicación

```bash
whisper-app-gui
```

o simplemente:

```bash
whisper-app
```

### Uso básico

1. **Cargar modelo**: Selecciona un modelo (tiny, base, small, medium o large) y haz clic en "Cargar modelo"
2. **Importar o grabar**: Importa un archivo o graba desde el micrófono
3. **Transcribir**: Selecciona el idioma (opcional) y haz clic en "Transcribir"
4. **Exportar**: Guarda los resultados en formato TXT, SRT o VTT

### Consejos de uso

- Los modelos más grandes (medium, large) proporcionan resultados más precisos pero requieren más recursos
- Para archivos largos, la transcripción puede tomar tiempo; la barra de progreso muestra el avance
- Para mejor calidad en la transcripción, usa audio sin ruido de fondo
- La traducción funciona mejor para idiomas populares

## Resolución de problemas

### FFMPEG no encontrado

Asegúrate de que FFMPEG esté instalado y en el PATH del sistema:

- **Windows**: Descarga desde https://ffmpeg.org/download.html y agrega al PATH
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg` (Ubuntu/Debian) o `sudo dnf install ffmpeg` (Fedora)

Si sigues teniendo problemas, configura la ruta manualmente en la aplicación: Herramientas → Configuración → Sistema.

### Errores de GPU/CUDA

Si encuentras errores relacionados con CUDA, es posible que necesites instalar la versión correcta de PyTorch:

```bash
pip install torch==x.x.x+cu11x
```

Consulta la [documentación de PyTorch](https://pytorch.org/get-started/locally/) para la versión específica.

## Desarrollo

### Configuración del entorno de desarrollo

```bash
git clone https://github.com/trigoo007/whisper-app
cd whisper-app
pip install -e ".[dev]"
```

### Estructura del proyecto

```
whisper_app/
├── src/
│   └── whisper_app/
│       ├── core/           # Componentes principales
│       ├── ui/             # Interfaz de usuario
│       ├── utils/          # Utilidades
│       ├── resources/      # Recursos (iconos, traducciones)
│       ├── __init__.py
│       ├── __main__.py
│       └── app.py          # Punto de entrada principal
├── tests/                  # Pruebas
├── docs/                   # Documentación
├── setup.py
├── pyproject.toml
└── README.md
```

## Licencia

Este proyecto está licenciado bajo los términos de la licencia MIT. Copyright (c) 2025 Rodrigo M. Consulta el archivo [LICENSE](LICENSE) para más detalles.

## Agradecimientos

- [OpenAI Whisper](https://github.com/openai/whisper) - El motor de transcripción utilizado
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) - Framework de UI
- [FFmpeg](https://ffmpeg.org/) - Procesamiento de multimedia
