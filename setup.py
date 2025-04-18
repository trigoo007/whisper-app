#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de instalación para WhisperApp
"""

import subprocess
from setuptools.command.install import install
from setuptools.command.develop import develop
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

class CompileTranslationsCommand:
    def run_command(self):
        try:
            print("Compilando archivos de traducción (.ts -> .qm)...")
            subprocess.run(["python", "compile_translations.py"], check=True)
        except Exception as e:
            print(f"[ADVERTENCIA] No se pudieron compilar las traducciones: {e}")

class InstallWithTranslations(install, CompileTranslationsCommand):
    def run(self):
        self.run_command()
        super().run()

class DevelopWithTranslations(develop, CompileTranslationsCommand):
    def run(self):
        self.run_command()
        super().run()

setup(
    name="whisper-app",
    version="1.0.0",
    author="Tu Nombre",
    author_email="tu.email@ejemplo.com",
    description="Aplicación de transcripción de audio/video basada en OpenAI Whisper",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tuusuario/whisper-app",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=[
        "PyQt5>=5.15",
        "openai-whisper>=20230314",
        "torch>=1.9.0",
        "numpy>=1.19",
        "soundfile",
        "scipy",
        "tqdm"
    ],
    extras_require={
        "dev": [
            "pytest",
            "black",
            "flake8",
            "isort",
            "pyinstaller"
        ],
        "icons": [
            "cairosvg>=2.5.0",
            "Pillow>=9.0.0"
        ],
        "translations": [
            "PyQt5-tools>=5.15.0"
        ],
        "cuda": ["torch==2.1.2+cu118"],
        "cpu": ["torch==2.1.2+cpu"]
        # "rocm": ["torch==2.1.2+rocm5.4.2"]
    },
    cmdclass={
        'install': InstallWithTranslations,
        'develop': DevelopWithTranslations
    },
    entry_points={
        "console_scripts": [
            "whisper-app=whisper_app.app:main",
        ],
        "gui_scripts": [
            "whisper-app-gui=whisper_app.app:main",
        ],
    },
    include_package_data=True,
    package_data={
        "whisper_app": [
            "resources/translations/*.qm",
            "resources/icons/*.png",
            "resources/icons/*.ico",
        ],
    },
)