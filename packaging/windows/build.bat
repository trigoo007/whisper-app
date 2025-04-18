@echo off
REM Script para construir WhisperApp en sistemas Windows

REM Verificar si PyInstaller está instalado
pip show pyinstaller >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Instalando PyInstaller...
    pip install pyinstaller
)

REM Obtener directorio raíz del proyecto
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..\..

REM Ir al directorio raíz del proyecto
cd %PROJECT_ROOT%

REM Instalar el proyecto en modo desarrollo
pip install -e .

REM Crear el ejecutable
pyinstaller --name="WhisperApp" ^
            --windowed ^
            --onefile ^
            --add-data="src\whisper_app\resources;whisper_app\resources" ^
            --hidden-import="PyQt5.QtCore" ^
            --hidden-import="PyQt5.QtGui" ^
            --hidden-import="PyQt5.QtWidgets" ^
            --hidden-import="whisper" ^
            --icon="src\whisper_app\resources\icons\app_icon.ico" ^
            src\whisper_app\app.py

REM Copiar archivos adicionales
if not exist "dist\resources" mkdir "dist\resources"
xcopy /E /Y "src\whisper_app\resources" "dist\resources\"

echo Construcción completada. Ejecutable en: %PROJECT_ROOT%\dist\WhisperApp.exe