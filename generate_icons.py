#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para generar iconos de la aplicación en diferentes formatos
Requiere cairosvg o librsvg instalados
"""

import os
import subprocess
import sys
import platform

def main():
    """Generar iconos desde SVG"""
    # Directorio de iconos
    icons_dir = os.path.join('src', 'whisper_app', 'resources', 'icons')
    
    # Asegurar que existe el directorio
    os.makedirs(icons_dir, exist_ok=True)
    
    # Archivo SVG de origen
    svg_file = os.path.join(icons_dir, 'app_icon.svg')
    
    # Comprobar si existe
    if not os.path.exists(svg_file):
        print(f"No se encontró el archivo SVG: {svg_file}")
        return
    
    # Tamaños para PNG
    sizes = [16, 32, 48, 64, 128, 256]
    
    # Intentar usar cairosvg (Python)
    try:
        import cairosvg
        for size in sizes:
            png_file = os.path.join(icons_dir, f"app_icon_{size}.png")
            print(f"Generando {png_file}")
            cairosvg.svg2png(url=svg_file, write_to=png_file, output_width=size, output_height=size)
        
        # Generar ICO usando uno de los PNG generados
        try:
            from PIL import Image
            ico_file = os.path.join(icons_dir, "app_icon.ico")
            img = Image.open(os.path.join(icons_dir, "app_icon_64.png"))
            img.save(ico_file, format='ICO')
            print(f"Generado {ico_file}")
        except ImportError:
            print("Pillow no está instalado, no se pudo generar .ico")
        
        print("Generación de iconos completada con cairosvg")
        return
    except ImportError:
        print("cairosvg no está instalado, intentando con rsvg-convert...")
    
    # Intentar usar rsvg-convert (comando externo)
    try:
        for size in sizes:
            png_file = os.path.join(icons_dir, f"app_icon_{size}.png")
            print(f"Generando {png_file}")
            subprocess.run(['rsvg-convert', '-w', str(size), '-h', str(size), '-o', png_file, svg_file], check=True)
        
        # En Linux, podemos crear el .ico con ImageMagick
        try:
            ico_file = os.path.join(icons_dir, "app_icon.ico")
            subprocess.run(['convert', os.path.join(icons_dir, "app_icon_64.png"), ico_file], check=True)
            print(f"Generado {ico_file}")
        except subprocess.SubprocessError:
            print("ImageMagick no está disponible, no se pudo generar .ico")
        
        print("Generación de iconos completada con rsvg-convert")
        return
    except (subprocess.SubprocessError, FileNotFoundError):
        print("rsvg-convert no está disponible")
    
    # Como último recurso, crear archivos PNG y ICO vacíos
    print("No se pudo generar iconos. Creando archivos vacíos...")
    for size in sizes:
        png_file = os.path.join(icons_dir, f"app_icon_{size}.png")
        with open(png_file, 'wb') as f:
            # Encabezado PNG mínimo
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
    
    ico_file = os.path.join(icons_dir, "app_icon.ico")
    with open(ico_file, 'wb') as f:
        # Encabezado ICO mínimo
        f.write(b'\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x00\x00\x00\x00\x68\x03\x00\x00\x16\x00\x00\x00')
    
    print("Creación de archivos de iconos vacíos completada")

if __name__ == "__main__":
    main()