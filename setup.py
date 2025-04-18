#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de instalación para WhisperApp
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="whisper-app",
    version="1.0.0",
    author="Rodrigo M.",
    author_email="rodrem@gmail.com",  # Corregido para que coincida con __init__.py
    description="Aplicación de transcripción de audio/video usando OpenAI Whisper",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/trigoo007/whisper-app",  # Corregido para que coincida con README.md
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Utilities",
    ],
    python_requires=">=3.7",
    install_requires=[
        "openai-whisper",
        "torch",
        "PyQt5",
        "sounddevice",
        "numpy",
        "soundfile",
        "scipy"
    ],
    extras_require={
        "dev": [
            "pytest",
            "black",
            "flake8",
            "isort",
            "pyinstaller"
        ],
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