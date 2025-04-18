#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar la estructura del proyecto WhisperApp
"""

import os
import sys
from colorama import init, Fore, Style

# Inicializar colorama para colores en la terminal
init()

# Configuración
PROJECT_ROOT = os.path.abspath(os.getcwd())  # Asume que se ejecuta desde la raíz del proyecto

# Directorios que deberían existir
REQUIRED_DIRS = [
    "src/whisper_app",
    "src/whisper_app/core",
    "src/whisper_app/ui",
    "src/whisper_app/utils",
    "src/whisper_app/resources",
    "src/whisper_app/resources/icons",
    "src/whisper_app/resources/translations",
    "tests",
    "tests/unit",
    "tests/integration",
    "docs",
    "docs/user",
    "docs/dev",
    "packaging",
    "packaging/windows",
    "packaging/macos",
    "packaging/linux"
]

# Archivos principales que deberían existir
REQUIRED_FILES = [
    # Archivos de inicialización y punto de entrada
    "src/whisper_app/__init__.py",
    "src/whisper_app/__main__.py",
    "src/whisper_app/app.py",
    
    # Archivos del módulo core
    "src/whisper_app/core/__init__.py",
    "src/whisper_app/core/config_manager.py",
    "src/whisper_app/core/transcriber.py",
    "src/whisper_app/core/recorder.py",
    "src/whisper_app/core/file_manager.py",
    
    # Archivos del módulo UI
    "src/whisper_app/ui/__init__.py",
    "src/whisper_app/ui/main_window.py",
    "src/whisper_app/ui/dialogs.py",
    
    # Archivos del módulo utils
    "src/whisper_app/utils/__init__.py",
    "src/whisper_app/utils/ffmpeg_utils.py",
    "src/whisper_app/utils/audio_utils.py",
    "src/whisper_app/utils/text_utils.py",
    
    # Archivos de recursos
    "src/whisper_app/resources/__init__.py",
    "src/whisper_app/resources/icons/__init__.py",
    "src/whisper_app/resources/translations/__init__.py",
    
    # Archivos de configuración del proyecto
    "setup.py",
    "pyproject.toml",
    "requirements.txt",
    "README.md",
    "LICENSE",
    ".gitignore"
]

# Archivos que deberían tener permisos de ejecución
EXECUTABLE_FILES = [
    "setup.py",
    "src/whisper_app/__main__.py",
    "packaging/macos/build.sh",
    "packaging/linux/build.sh"
]

# Función para verificar si un archivo tiene permisos de ejecución
def is_executable(file_path):
    """Verifica si un archivo tiene permisos de ejecución"""
    if os.name == 'nt':  # Windows
        return True  # En Windows no se verifican permisos de ejecución
    else:  # Unix/Linux/Mac
        return os.access(file_path, os.X_OK)

def main():
    print(f"{Fore.CYAN}Verificando estructura del proyecto WhisperApp...{Style.RESET_ALL}")
    print(f"Directorio raíz: {PROJECT_ROOT}\n")
    
    # Contadores para estadísticas
    total_dirs = len(REQUIRED_DIRS)
    total_files = len(REQUIRED_FILES)
    missing_dirs = 0
    missing_files = 0
    non_executable_files = 0
    
    # Verificar directorios
    print(f"{Fore.YELLOW}Verificando directorios requeridos...{Style.RESET_ALL}")
    for directory in REQUIRED_DIRS:
        full_path = os.path.join(PROJECT_ROOT, directory)
        if os.path.isdir(full_path):
            print(f"  {Fore.GREEN}✓{Style.RESET_ALL} {directory}")
        else:
            print(f"  {Fore.RED}✗{Style.RESET_ALL} {directory} {Fore.RED}(no existe){Style.RESET_ALL}")
            missing_dirs += 1
    
    # Verificar archivos
    print(f"\n{Fore.YELLOW}Verificando archivos requeridos...{Style.RESET_ALL}")
    for file in REQUIRED_FILES:
        full_path = os.path.join(PROJECT_ROOT, file)
        if os.path.isfile(full_path):
            print(f"  {Fore.GREEN}✓{Style.RESET_ALL} {file}")
        else:
            print(f"  {Fore.RED}✗{Style.RESET_ALL} {file} {Fore.RED}(no existe){Style.RESET_ALL}")
            missing_files += 1
    
    # Verificar permisos de ejecución
    if os.name != 'nt':  # Omitir en Windows
        print(f"\n{Fore.YELLOW}Verificando permisos de ejecución...{Style.RESET_ALL}")
        for file in EXECUTABLE_FILES:
            full_path = os.path.join(PROJECT_ROOT, file)
            if os.path.isfile(full_path):
                if is_executable(full_path):
                    print(f"  {Fore.GREEN}✓{Style.RESET_ALL} {file} (ejecutable)")
                else:
                    print(f"  {Fore.RED}✗{Style.RESET_ALL} {file} {Fore.RED}(no es ejecutable){Style.RESET_ALL}")
                    non_executable_files += 1
    
    # Mostrar resumen
    print(f"\n{Fore.CYAN}Resumen de verificación:{Style.RESET_ALL}")
    print(f"  Directorios: {total_dirs - missing_dirs}/{total_dirs} existentes")
    print(f"  Archivos: {total_files - missing_files}/{total_files} existentes")
    
    if os.name != 'nt':
        exec_check_count = len([f for f in EXECUTABLE_FILES if os.path.isfile(os.path.join(PROJECT_ROOT, f))])
        print(f"  Archivos ejecutables: {exec_check_count - non_executable_files}/{exec_check_count} correctos")
    
    # Determinar si la estructura es correcta
    if missing_dirs == 0 and missing_files == 0 and non_executable_files == 0:
        print(f"\n{Fore.GREEN}¡La estructura del proyecto es correcta!{Style.RESET_ALL}")
        return 0
    else:
        print(f"\n{Fore.RED}La estructura del proyecto tiene problemas.{Style.RESET_ALL}")
        
        # Mostrar instrucciones para corregir problemas
        if missing_dirs > 0:
            print(f"\n{Fore.YELLOW}Para crear los directorios faltantes:{Style.RESET_ALL}")
            for directory in REQUIRED_DIRS:
                full_path = os.path.join(PROJECT_ROOT, directory)
                if not os.path.isdir(full_path):
                    print(f"  mkdir -p {directory}")
        
        if missing_files > 0:
            print(f"\n{Fore.YELLOW}Para crear los archivos faltantes:{Style.RESET_ALL}")
            for file in REQUIRED_FILES:
                full_path = os.path.join(PROJECT_ROOT, file)
                if not os.path.isfile(full_path):
                    dir_path = os.path.dirname(file)
                    print(f"  mkdir -p {dir_path} && touch {file}")
        
        if non_executable_files > 0:
            print(f"\n{Fore.YELLOW}Para establecer permisos de ejecución:{Style.RESET_ALL}")
            for file in EXECUTABLE_FILES:
                full_path = os.path.join(PROJECT_ROOT, file)
                if os.path.isfile(full_path) and not is_executable(full_path):
                    print(f"  chmod +x {file}")
        
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Verificación cancelada por el usuario.{Style.RESET_ALL}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Fore.RED}Error durante la verificación: {e}{Style.RESET_ALL}")
        sys.exit(1)
