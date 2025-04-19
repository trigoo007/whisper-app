#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Widgets personalizados para WhisperApp
"""

from PyQt5.QtWidgets import (
    QWidget, QLabel, QProgressBar, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QSpinBox, QComboBox, QCheckBox,
    QListWidget, QListWidgetItem, QStyle
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap

class AudioLevelMeter(QWidget):
    """Widget para mostrar nivel de audio"""
    
    def __init__(self, parent=None):
        """Inicializa el medidor de nivel de audio"""
        super().__init__(parent)
        self.level = 0.0
        self.peak_level = 0.0
        self.decay_rate = 0.05
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configura la interfaz del widget"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Barra de nivel
        self.level_bar = QProgressBar()
        self.level_bar.setRange(0, 100)
        self.level_bar.setValue(0)
        self.level_bar.setTextVisible(False)
        # Eliminamos el estilo inline ya que ahora usamos el tema global
        layout.addWidget(self.level_bar)
        
        # Etiqueta de pico
        self.peak_label = QLabel("Pico: 0%")
        self.peak_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.peak_label)
    
    def set_level(self, level):
        """
        Establece el nivel actual de audio
        
        Args:
            level (float): Nivel de audio (0.0 a 1.0)
        """
        # Convertir a porcentaje
        percent = min(100, int(level * 100))
        
        # Actualizar barra
        self.level_bar.setValue(percent)
        
        # Actualizar pico si es necesario
        if percent > self.peak_level:
            self.peak_level = percent
            self.peak_label.setText(f"Pico: {self.peak_level}%")
    
    def reset_peak(self):
        """Restablece nivel de pico"""
        self.peak_level = 0
        self.peak_label.setText("Pico: 0%")

class FileListItem(QListWidgetItem):
    """Elemento personalizado para lista de archivos"""
    
    def __init__(self, file_name, file_info=None):
        """
        Inicializa elemento de lista de archivos
        
        Args:
            file_name (str): Nombre del archivo
            file_info (dict, optional): Información del archivo
        """
        super().__init__(file_name)
        self.file_info = file_info or {}
        
        # Establecer icono según tipo de archivo
        ext = file_name.split('.')[-1].lower() if '.' in file_name else ''
        
        if ext in ['mp3', 'wav', 'm4a', 'ogg', 'flac']:
            self.setIcon(QStyle.standardIcon(QStyle.SP_MediaVolume))
        elif ext in ['mp4', 'mov', 'avi', 'mkv', 'webm']:
            self.setIcon(QStyle.standardIcon(QStyle.SP_MediaPlay))
        else:
            self.setIcon(QStyle.standardIcon(QStyle.SP_FileIcon))