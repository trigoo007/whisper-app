#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modelo para representar transcripciones
"""

import json
import time
from datetime import datetime

class TranscriptionModel:
    """Representa una transcripción en la aplicación"""
    
    def __init__(self, file_name, result=None):
        """
        Inicializa un modelo de transcripción
        
        Args:
            file_name (str): Nombre del archivo transcrito
            result (dict, optional): Resultado de la transcripción
        """
        self.file_name = file_name
        self.result = result or {}
        self.text = self.result.get('text', '')
        self.segments = self.result.get('segments', [])
        self.language = self.result.get('language', 'unknown')
        self.translations = {}
        
        # Metadatos
        self.created = datetime.now()
        self.processing_time = 0.0
        self.model_used = None
        self.modified = False
        self.translated = False
        self.language_source = None
        self.language_target = None
    
    def __str__(self):
        """Representación de cadena"""
        if not self.text:
            return f"Transcripción vacía para {self.file_name}"
        
        # Truncar texto si es muy largo
        preview = self.text[:100] + ('...' if len(self.text) > 100 else '')
        return f"Transcripción de {self.file_name}: {preview}"
    
    def word_count(self):
        """Cuenta palabras en la transcripción"""
        if not self.text:
            return 0
        return len(self.text.split())
    
    def segment_count(self):
        """Cuenta segmentos en la transcripción"""
        return len(self.segments)
    
    def duration(self):
        """Obtiene duración total de la transcripción"""
        if not self.segments:
            return 0.0
            
        try:
            return max(segment['end'] for segment in self.segments)
        except (KeyError, ValueError):
            return 0.0
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'file_name': self.file_name,
            'result': self.result,
            'created': self.created.isoformat(),
            'processing_time': self.processing_time,
            'model_used': self.model_used,
            'modified': self.modified,
            'translated': self.translated,
            'language_source': self.language_source,
            'language_target': self.language_target
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Crea una instancia desde un diccionario
        
        Args:
            data (dict): Datos de la transcripción
        
        Returns:
            TranscriptionModel: Nueva instancia
        """
        instance = cls(data['file_name'], data.get('result', {}))
        
        if 'created' in data:
            try:
                instance.created = datetime.fromisoformat(data['created'])
            except ValueError:
                instance.created = datetime.now()
                
        instance.processing_time = data.get('processing_time', 0.0)
        instance.model_used = data.get('model_used')
        instance.modified = data.get('modified', False)
        instance.translated = data.get('translated', False)
        instance.language_source = data.get('language_source')
        instance.language_target = data.get('language_target')
        
        return instance