#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para compilar archivos de traducción .ts a .qm
Requiere PyQt5 y lrelease instalados
"""

import os
import subprocess
import sys

def main():
    """Compilar archivos de traducción"""
    # Directorio de traducciones
    translations_dir = os.path.join('src', 'whisper_app', 'resources', 'translations')
    
    # Asegurar que existe el directorio
    os.makedirs(translations_dir, exist_ok=True)
    
    # Buscar archivos .ts
    ts_files = []
    for file in os.listdir(translations_dir):
        if file.endswith('.ts'):
            ts_files.append(os.path.join(translations_dir, file))
    
    if not ts_files:
        print("No se encontraron archivos .ts")
        return
    
    # Intentar usar lrelease
    try:
        for ts_file in ts_files:
            qm_file = os.path.splitext(ts_file)[0] + '.qm'
            print(f"Compilando {ts_file} -> {qm_file}")
            
            # Intentar con lrelease-qt5 (común en distribuciones Linux)
            try:
                subprocess.run(['lrelease-qt5', ts_file, '-qm', qm_file], check=True)
                continue
            except (subprocess.SubprocessError, FileNotFoundError):
                pass
            
            # Intentar con lrelease (común en Windows/Mac)
            try:
                subprocess.run(['lrelease', ts_file, '-qm', qm_file], check=True)
                continue
            except (subprocess.SubprocessError, FileNotFoundError):
                pass
            
            # Intentar con PyQt5 lrelease
            try:
                from PyQt5.QtCore import QLibraryInfo
                qt_bin_dir = QLibraryInfo.location(QLibraryInfo.BinariesPath)
                lrelease_path = os.path.join(qt_bin_dir, 'lrelease')
                subprocess.run([lrelease_path, ts_file, '-qm', qm_file], check=True)
                continue
            except (ImportError, subprocess.SubprocessError, FileNotFoundError):
                pass
                
            print(f"No se pudo compilar {ts_file}. Creando archivo vacío.")
            # Crear archivo .qm vacío como fallback
            with open(qm_file, 'wb') as f:
                # Encabezado mínimo de archivo QM
                f.write(b'\x3C\xB8\x64\x18\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    
    except Exception as e:
        print(f"Error al compilar traducciones: {e}")
        return
    
    print("Compilación de traducciones completada")

if __name__ == "__main__":
    main()
