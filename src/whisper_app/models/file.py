#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modelo para representar archivos multimedia
"""

import os
from datetime import datetime

class FileModel:
    """Representa un archivo multimedia en la aplicación"""
    
    def __init__(self, file_path, processed_path=None):
        """
        Inicializa un modelo de archivo
        
        Args:
            file_path (str): Ruta al archivo original
            processed_path (str, optional): Ruta al archivo procesado
        """
        self.original_path = file_path
        self.processed_path = processed_path or file_path
        self.name = os.path.basename(file_path)
        
        # Propiedades del archivo
        try:
            self.size = os.path.getsize(file_path)
            self.created = datetime.fromtimestamp(os.path.getctime(file_path))
            self.modified = datetime.fromtimestamp(os.path.getmtime(file_path))
        except Exception:
            self.size = 0
            self.created = datetime.now()
            self.modified = datetime.now()
        
        # Propiedades multimedia (a establecer externamente)
        self.duration = 0.0
        self.format = None
        self.streams = []
        
    def __str__(self):
        """Representación de cadena"""
        return f"{self.name} ({self.format_size()})"
    
    def format_size(self):
        """Formatea el tamaño del archivo a una representación legible"""
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} GB"
    
    def format_duration(self):
        """Formatea la duración a una representación legible"""
        if not self.duration:
            return "Desconocida"
        
        minutes = int(self.duration // 60)
        seconds = int(self.duration % 60)
        return f"{minutes}:{seconds:02d}"
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'original_path': self.original_path,
            'processed_path': self.processed_path,
            'name': self.name,
            'size': self.size,
            'duration': self.duration,
            'created': self.created,
            'modified': self.modified,
            'format': self.format,
            'streams': self.streams
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Crea una instancia desde un diccionario
        
        Args:
            data (dict): Datos del archivo
        
        Returns:
            FileModel: Nueva instancia
        """
        instance = cls(data['original_path'], data.get('processed_path'))
        instance.name = data.get('name', instance.name)
        instance.size = data.get('size', instance.size)
        instance.duration = data.get('duration', instance.duration)
        instance.created = data.get('created', instance.created)
        instance.modified = data.get('modified', instance.modified)
        instance.format = data.get('format')
        instance.streams = data.get('streams', [])
        return instance