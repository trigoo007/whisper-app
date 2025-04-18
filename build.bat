@echo off
REM Script de build para WhisperApp en Windows

REM Crear entorno virtual (opcional)
REM python -m venv venv
REM call venv\Scripts\activate

REM Instalar dependencias
pip install -r requirements.txt

REM Ejecutar PyInstaller
pyinstaller --noconfirm --windowed --name WhisperApp --icon src/whisper_app/resources/icons/app.ico src/whisper_app/app.py

REM Nota: Puedes personalizar los parámetros de PyInstaller según tus necesidades.
REM Alternativa moderna: considera usar Briefcase para empaquetado multiplataforma. 