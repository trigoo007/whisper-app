#!/bin/bash
# Script para construir WhisperApp en sistemas macOS

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
pyinstaller --name="WhisperApp" \
            --windowed \
            --onefile \
            --add-data="src/whisper_app/resources:whisper_app/resources" \
            --hidden-import="PyQt5.QtCore" \
            --hidden-import="PyQt5.QtGui" \
            --hidden-import="PyQt5.QtWidgets" \
            --hidden-import="whisper" \
            --icon="src/whisper_app/resources/icons/app_icon.icns" \
            src/whisper_app/app.py

# Crear .app bundle
mkdir -p "dist/WhisperApp.app/Contents/Resources"
cp -r src/whisper_app/resources/* "dist/WhisperApp.app/Contents/Resources/"

# Agregar archivo Info.plist
cat > "dist/WhisperApp.app/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDisplayName</key>
    <string>WhisperApp</string>
    <key>CFBundleExecutable</key>
    <string>WhisperApp</string>
    <key>CFBundleIconFile</key>
    <string>app_icon.icns</string>
    <key>CFBundleIdentifier</key>
    <string>com.whisperapp</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>WhisperApp</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>WhisperApp necesita acceso al micrófono para grabar audio</string>
</dict>
</plist>
EOF

echo "Construcción completada. Aplicación en: $PROJECT_ROOT/dist/WhisperApp.app"