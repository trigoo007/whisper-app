#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WhisperApp - Aplicación de transcripción de audio/video con OpenAI Whisper
"""

__version__ = "1.0.0"
__author__ = "Rodrigo M."
__email__ = "rodrem@gmail.com"
__license__ = "MIT"
__status__ = "Production"
__copyright__ = "Copyright 2025"

import os
import sys
import logging
from pathlib import Path

# Configurar logging global
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.expanduser("~"), "whisper_app.log"))
    ]
)

# Establecer ruta a recursos
RESOURCES_PATH = os.path.join(os.path.dirname(__file__), "resources")