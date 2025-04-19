#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo UI de WhisperApp

Contiene los componentes de la interfaz de usuario:
- Ventana principal
- Diálogos
- Widgets personalizados
- Estilos de interfaz
"""

from .main_window import MainWindow
from .dialogs import (
    ConfigDialog, 
    AudioDeviceDialog, 
    AdvancedOptionsDialog,
    AboutDialog,
    ErrorReportDialog,
    ModelDownloadDialog
)
from .styles import apply_theme, ELEGANT_DARK_PALETTE