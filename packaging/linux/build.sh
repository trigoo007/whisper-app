#!/bin/bash
# Script para construir WhisperApp en sistemas Linux

set -e  # Salir si hay errores

# Verificar si PyInstaller está instalado
if ! pip show pyinstaller > /dev/null; then
    echo "Instalando PyInstaller..."
    pip install pyinstaller
fi

# Directorio del script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Ir al directorio raíz del proyecto
cd "$PROJECT_ROOT"

# Instalar el proyecto en modo desarrollo
pip install -e .

# Crear el ejecutable
pyinstaller --name="whisper-app" \
            --windowed \
            --onefile \
            --add-data="src/whisper_app/resources:whisper_app/resources" \
            --hidden-import="PyQt5.QtCore" \
            --hidden-import="PyQt5.QtGui" \
            --hidden-import="PyQt5.QtWidgets" \
            --hidden-import="whisper" \
            src/whisper_app/app.py

# Copiar archivos adicionales
mkdir -p dist/resources
cp -r src/whisper_app/resources/* dist/resources/

echo "Construcción completada. Ejecutable en: $PROJECT_ROOT/dist/whisper-app"