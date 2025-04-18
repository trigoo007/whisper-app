#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diálogos para WhisperApp
"""

import os
import sys
import logging
import tempfile
import shutil
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox, QTabWidget,
    QWidget, QGroupBox, QFileDialog, QDialogButtonBox,
    QLineEdit, QListWidget, QListWidgetItem, QRadioButton,
    QFormLayout, QGridLayout, QSlider, QMessageBox, QProgressDialog,
    QApplication, QTextEdit, QToolButton, QFrame, QStyle
)
from PyQt5.QtCore import Qt, QSize, QUrl, QThread, pyqtSignal, QSettings, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QDesktopServices, QFont, QColor, QPalette

from whisper_app.utils.ffmpeg_utils import verify_ffmpeg, find_ffmpeg

logger = logging.getLogger(__name__)

class ConfigDialog(QDialog):
    """Diálogo de configuración general"""
    
    def __init__(self, config_manager, parent=None):
        """
        Inicializa el diálogo de configuración
        
        Args:
            config_manager: Instancia de ConfigManager
            parent: Widget padre
        """
        super().__init__(parent)
        self.config = config_manager
        
        self.setWindowTitle("Configuración")
        self.resize(600, 450)
        
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        layout = QVBoxLayout(self)
        
        # Pestañas de configuración
        self.tabs = QTabWidget()
        
        # Pestaña de general
        self.general_tab = QWidget()
        self.setup_general_tab()
        self.tabs.addTab(self.general_tab, "General")
        
        # Pestaña de transcripción
        self.transcription_tab = QWidget()
        self.setup_transcription_tab()
        self.tabs.addTab(self.transcription_tab, "Transcripción")
        
        # Pestaña de exportación
        self.export_tab = QWidget()
        self.setup_export_tab()
        self.tabs.addTab(self.export_tab, "Exportación")
        
        # Pestaña de sistema
        self.system_tab = QWidget()
        self.setup_system_tab()
        self.tabs.addTab(self.system_tab, "Sistema")
        
        layout.addWidget(self.tabs)
        
        # Botones de diálogo
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply | QDialogButtonBox.Reset
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply_settings)
        self.button_box.button(QDialogButtonBox.Reset).clicked.connect(self.reset_settings)
        
        layout.addWidget(self.button_box)
    
    def setup_general_tab(self):
        """Configura la pestaña de configuración general"""
        layout = QVBoxLayout(self.general_tab)
        
        # Grupo de interfaz
        ui_group = QGroupBox("Interfaz")
        ui_layout = QFormLayout(ui_group)
        
        # Tema
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Sistema", "Claro", "Oscuro"])
        ui_layout.addRow("Tema:", self.theme_combo)
        
        # Idioma
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Español", "English", "Automático (sistema)"])
        ui_layout.addRow("Idioma de la interfaz:", self.lang_combo)
        
        # Mostrar avanzadas
        self.advanced_check = QCheckBox("Mostrar opciones avanzadas")
        ui_layout.addRow("", self.advanced_check)
        
        layout.addWidget(ui_group)
        
        # Grupo de comportamiento
        behavior_group = QGroupBox("Comportamiento")
        behavior_layout = QFormLayout(behavior_group)
        
        # Cargar modelo al inicio
        self.load_at_start_check = QCheckBox("Cargar modelo al iniciar")
        behavior_layout.addRow("", self.load_at_start_check)
        
        # Normalizar audio
        self.normalize_check = QCheckBox("Normalizar audio durante importación")
        behavior_layout.addRow("", self.normalize_check)
        
        # Confirm al salir
        self.confirm_exit_check = QCheckBox("Confirmar al salir de la aplicación")
        behavior_layout.addRow("", self.confirm_exit_check)
        
        layout.addWidget(behavior_group)
        
        # Archivos recientes
        recent_group = QGroupBox("Archivos recientes")
        recent_layout = QVBoxLayout(recent_group)
        
        self.recent_list = QListWidget()
        recent_layout.addWidget(self.recent_list)
        
        clear_recent_btn = QPushButton("Limpiar lista")
        clear_recent_btn.clicked.connect(self.clear_recent_files)
        recent_layout.addWidget(clear_recent_btn)
        
        layout.addWidget(recent_group)
        
        layout.addStretch()
    
    def setup_transcription_tab(self):
        """Configura la pestaña de configuración de transcripción"""
        layout = QVBoxLayout(self.transcription_tab)
        
        # Grupo de modelo
        model_group = QGroupBox("Modelo predeterminado")
        model_layout = QFormLayout(model_group)
        
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        model_layout.addRow("Tamaño del modelo:", self.model_combo)
        
        # Checkbox para fp16
        self.fp16_check = QCheckBox("Usar precisión de media (FP16)")
        self.fp16_check.setToolTip("Ahorra memoria pero puede reducir ligeramente la precisión")
        model_layout.addRow("", self.fp16_check)
        
        layout.addWidget(model_group)
        
        # Grupo de idioma
        lang_group = QGroupBox("Idioma")
        lang_layout = QFormLayout(lang_group)
        
        self.detect_lang_radio = QRadioButton("Detectar automáticamente")
        lang_layout.addRow("", self.detect_lang_radio)
        
        self.default_lang_radio = QRadioButton("Usar idioma predeterminado:")
        lang_layout.addRow("", self.default_lang_radio)
        
        self.default_lang_combo = QComboBox()
        languages = [
            ("Español", "es"),
            ("Inglés", "en"),
            ("Francés", "fr"),
            ("Alemán", "de"),
            ("Italiano", "it"),
            ("Portugués", "pt"),
            ("Chino", "zh"),
            ("Japonés", "ja"),
            ("Ruso", "ru"),
            ("Coreano", "ko")
        ]
        
        for name, code in languages:
            self.default_lang_combo.addItem(name, code)
        
        lang_layout.addRow("", self.default_lang_combo)
        
        layout.addWidget(lang_group)
        
        # Grupo de procesamiento
        process_group = QGroupBox("Procesamiento")
        process_layout = QFormLayout(process_group)
        
        # VAD
        self.vad_check = QCheckBox("Usar detección de voz (VAD)")
        self.vad_check.setToolTip("Filtrar partes sin voz del audio")
        process_layout.addRow("", self.vad_check)
        
        # Segmentación de archivos
        self.segment_check = QCheckBox("Segmentar archivos grandes")
        self.segment_check.setToolTip("Procesar archivos grandes en segmentos menores")
        process_layout.addRow("", self.segment_check)
        
        # Tamaño máximo de segmento
        self.segment_size_spin = QSpinBox()
        self.segment_size_spin.setRange(60, 1800) # 1 a 30 minutos
        self.segment_size_spin.setSuffix(" segundos")
        self.segment_size_spin.setValue(600) # 10 minutos
        process_layout.addRow("Duración máxima de segmento:", self.segment_size_spin)
        
        layout.addWidget(process_group)
        
        # Opciones avanzadas
        advanced_group = QGroupBox("Opciones avanzadas")
        advanced_layout = QVBoxLayout(advanced_group)
        
        advanced_button = QPushButton("Configurar opciones avanzadas...")
        advanced_button.clicked.connect(self.show_advanced_options)
        advanced_layout.addWidget(advanced_button)
        
        layout.addWidget(advanced_group)
        
        layout.addStretch()
    
    def setup_export_tab(self):
        """Configura la pestaña de configuración de exportación"""
        layout = QVBoxLayout(self.export_tab)
        
        # Grupo de formatos
        formats_group = QGroupBox("Formatos de exportación")
        formats_layout = QVBoxLayout(formats_group)
        
        self.txt_check = QCheckBox("Texto plano (TXT)")
        formats_layout.addWidget(self.txt_check)
        
        self.srt_check = QCheckBox("Subtítulos SRT")
        formats_layout.addWidget(self.srt_check)
        
        self.vtt_check = QCheckBox("Subtítulos WebVTT")
        formats_layout.addWidget(self.vtt_check)
        
        formats_layout.addStretch()
        
        layout.addWidget(formats_group)
        
        # Grupo de automatización
        auto_group = QGroupBox("Exportación automática")
        auto_layout = QVBoxLayout(auto_group)
        
        self.auto_export_check = QCheckBox("Exportar automáticamente al completar transcripción")
        auto_layout.addWidget(self.auto_export_check)
        
        directory_layout = QHBoxLayout()
        directory_layout.addWidget(QLabel("Directorio de exportación:"))
        
        self.export_dir_edit = QLineEdit()
        self.export_dir_edit.setReadOnly(True)
        directory_layout.addWidget(self.export_dir_edit, 1)
        
        self.browse_export_btn = QPushButton("Examinar...")
        self.browse_export_btn.clicked.connect(self.browse_export_dir)
        directory_layout.addWidget(self.browse_export_btn)
        
        auto_layout.addLayout(directory_layout)
        
        layout.addWidget(auto_group)
        
        # Grupo de opciones de formato
        format_options_group = QGroupBox("Opciones de formato")
        format_options_layout = QFormLayout(format_options_group)
        
        # Máximo de caracteres por línea
        self.max_chars_spin = QSpinBox()
        self.max_chars_spin.setRange(20, 200)
        self.max_chars_spin.setValue(80)
        format_options_layout.addRow("Máximo de caracteres por línea:", self.max_chars_spin)
        
        # Duración máxima de subtítulo
        self.max_duration_spin = QDoubleSpinBox()
        self.max_duration_spin.setRange(1.0, 10.0)
        self.max_duration_spin.setValue(5.0)
        self.max_duration_spin.setSuffix(" segundos")
        self.max_duration_spin.setDecimals(1)
        format_options_layout.addRow("Duración máxima de subtítulo:", self.max_duration_spin)
        
        layout.addWidget(format_options_group)
        
        layout.addStretch()
    
    def setup_system_tab(self):
        """Configura la pestaña de configuración del sistema"""
        layout = QVBoxLayout(self.system_tab)
        
        # Grupo de FFMPEG
        ffmpeg_group = QGroupBox("FFMPEG")
        ffmpeg_layout = QVBoxLayout(ffmpeg_group)
        
        # Estado
        ffmpeg_status_layout = QHBoxLayout()
        ffmpeg_status_layout.addWidget(QLabel("Estado:"))
        
        self.ffmpeg_status_label = QLabel()
        ffmpeg_status_layout.addWidget(self.ffmpeg_status_label, 1)
        
        self.check_ffmpeg_btn = QPushButton("Verificar")
        self.check_ffmpeg_btn.clicked.connect(self.check_ffmpeg)
        ffmpeg_status_layout.addWidget(self.check_ffmpeg_btn)
        
        ffmpeg_layout.addLayout(ffmpeg_status_layout)
        
        # Ruta
        ffmpeg_path_layout = QHBoxLayout()
        ffmpeg_path_layout.addWidget(QLabel("Ruta:"))
        
        self.ffmpeg_path_edit = QLineEdit()
        ffmpeg_path_layout.addWidget(self.ffmpeg_path_edit, 1)
        
        self.browse_ffmpeg_btn = QPushButton("Examinar...")
        self.browse_ffmpeg_btn.clicked.connect(self.browse_ffmpeg)
        ffmpeg_path_layout.addWidget(self.browse_ffmpeg_btn)
        
        ffmpeg_layout.addLayout(ffmpeg_path_layout)
        
        # Ayuda para instalar
        help_link = QLabel("<a href='https://ffmpeg.org/download.html'>¿Necesitas ayuda para instalar FFMPEG?</a>")
        help_link.setOpenExternalLinks(True)
        ffmpeg_layout.addWidget(help_link)
        
        layout.addWidget(ffmpeg_group)
        
        # Grupo de audio
        audio_group = QGroupBox("Audio")
        audio_layout = QFormLayout(audio_group)
        
        self.sample_rate_combo = QComboBox()
        for rate in [8000, 16000, 22050, 44100, 48000]:
            self.sample_rate_combo.addItem(f"{rate} Hz", rate)
        audio_layout.addRow("Frecuencia de muestreo:", self.sample_rate_combo)
        
        self.channels_combo = QComboBox()
        self.channels_combo.addItem("Mono (1 canal)", 1)
        self.channels_combo.addItem("Estéreo (2 canales)", 2)
        audio_layout.addRow("Canales:", self.channels_combo)
        
        layout.addWidget(audio_group)
        
        # Grupo de caché y archivos temporales
        cache_group = QGroupBox("Caché y archivos temporales")
        cache_layout = QVBoxLayout(cache_group)
        
        cache_info_layout = QHBoxLayout()
        cache_info_layout.addWidget(QLabel("Archivos temporales:"))
        
        self.cache_info_label = QLabel("Calculando...")
        cache_info_layout.addWidget(self.cache_info_label, 1)
        
        cache_layout.addLayout(cache_info_layout)
        
        self.delete_temp_check = QCheckBox("Eliminar archivos temporales al salir")
        cache_layout.addWidget(self.delete_temp_check)
        
        self.clear_cache_btn = QPushButton("Limpiar caché ahora")
        self.clear_cache_btn.clicked.connect(self.clear_cache)
        cache_layout.addWidget(self.clear_cache_btn)
        
        layout.addWidget(cache_group)
        
        # Iniciar cálculo de tamaño de caché
        QTimer.singleShot(500, self.update_cache_info)
        
        layout.addStretch()
    
    def update_cache_info(self):
        """Actualiza información sobre archivos temporales"""
        try:
            # Calcular tamaño de archivos temporales de la aplicación
            temp_dir = tempfile.gettempdir()
            total_size = 0
            count = 0
            
            prefixes = ['whisper_', 'whisper-app_']
            
            for file in os.listdir(temp_dir):
                if any(file.startswith(prefix) for prefix in prefixes):
                    file_path = os.path.join(temp_dir, file)
                    if os.path.isfile(file_path):
                        total_size += os.path.getsize(file_path)
                        count += 1
            
            # Convertir a formato legible
            if total_size > 1024 * 1024 * 1024:
                size_str = f"{total_size / (1024 * 1024 * 1024):.2f} GB"
            elif total_size > 1024 * 1024:
                size_str = f"{total_size / (1024 * 1024):.2f} MB"
            elif total_size > 1024:
                size_str = f"{total_size / 1024:.2f} KB"
            else:
                size_str = f"{total_size} bytes"
            
            self.cache_info_label.setText(f"{count} archivos ({size_str})")
            
        except Exception as e:
            logger.warning(f"Error al calcular tamaño de caché: {e}")
            self.cache_info_label.setText("No disponible")
    
    def load_config(self):
        """Carga la configuración actual en la interfaz"""
        try:
            # Pestaña general
            theme = self.config.get("ui_theme", "system")
            theme_index = {"system": 0, "light": 1, "dark": 2}.get(theme, 0)
            self.theme_combo.setCurrentIndex(theme_index)
            
            lang = self.config.get("ui_language", "auto")
            lang_index = {"es": 0, "en": 1, "auto": 2}.get(lang, 2)
            self.lang_combo.setCurrentIndex(lang_index)
            
            self.advanced_check.setChecked(self.config.get("advanced_mode", False))
            self.load_at_start_check.setChecked(self.config.get("load_model_at_start", False))
            self.normalize_check.setChecked(self.config.get("normalize_audio", False))
            self.confirm_exit_check.setChecked(self.config.get("confirm_exit", True))
            
            # Archivos recientes
            recent_files = self.config.get("recent_files", [])
            self.recent_list.clear()
            for file_path in recent_files:
                if os.path.exists(file_path):
                    file_name = os.path.basename(file_path)
                    item = QListWidgetItem(f"{file_name}")
                    item.setToolTip(file_path)
                    self.recent_list.addItem(item)
            
            # Pestaña transcripción
            model_size = self.config.get("model_size", "base")
            model_index = self.model_combo.findText(model_size)
            self.model_combo.setCurrentIndex(max(0, model_index))
            
            self.fp16_check.setChecked(self.config.get("fp16", True))
            
            default_lang = self.config.get("language")
            if default_lang:
                self.default_lang_radio.setChecked(True)
                # Encontrar el idioma en el combo
                for i in range(self.default_lang_combo.count()):
                    if self.default_lang_combo.itemData(i) == default_lang:
                        self.default_lang_combo.setCurrentIndex(i)
                        break
            else:
                self.detect_lang_radio.setChecked(True)
            
            self.default_lang_combo.setEnabled(self.default_lang_radio.isChecked())
            
            self.vad_check.setChecked(self.config.get("use_vad", False))
            self.segment_check.setChecked(self.config.get("segment_large_files", True))
            self.segment_size_spin.setValue(self.config.get("max_segment_duration", 600))
            
            # Pestaña exportación
            formats = self.config.get("export_formats", ["txt", "srt", "vtt"])
            self.txt_check.setChecked("txt" in formats)
            self.srt_check.setChecked("srt" in formats)
            self.vtt_check.setChecked("vtt" in formats)
            
            self.auto_export_check.setChecked(self.config.get("auto_export", False))
            export_dir = self.config.get("export_directory", "")
            self.export_dir_edit.setText(export_dir)
            
            # Opciones de formato
            self.max_chars_spin.setValue(self.config.get("max_chars_per_line", 80))
            self.max_duration_spin.setValue(self.config.get("max_subtitle_duration", 5.0))
            
            # Pestaña sistema
            # Estado de FFMPEG
            self.check_ffmpeg()
            
            # Audio
            sample_rate = self.config.get("sample_rate", 16000)
            for i in range(self.sample_rate_combo.count()):
                if self.sample_rate_combo.itemData(i) == sample_rate:
                    self.sample_rate_combo.setCurrentIndex(i)
                    break
            
            channels = self.config.get("channels", 1)
            self.channels_combo.setCurrentIndex(channels - 1)
            
            # Caché
            self.delete_temp_check.setChecked(self.config.get("delete_temp_on_exit", True))
            
            # Conectar señales después de cargar valores
            self.default_lang_radio.toggled.connect(self.toggle_default_lang)
            
        except Exception as e:
            logger.error(f"Error al cargar configuración: {e}")
    
    def toggle_default_lang(self, checked):
        """Habilita/deshabilita el combo de idioma predeterminado"""
        self.default_lang_combo.setEnabled(checked)
    
    def check_ffmpeg(self):
        """Verifica y muestra estado de FFMPEG"""
        self.ffmpeg_path_edit.setText(self.config.get("ffmpeg_path", ""))
        
        if verify_ffmpeg():
            ffmpeg_path = find_ffmpeg()
            self.ffmpeg_status_label.setText("✅ Instalado")
            self.ffmpeg_status_label.setStyleSheet("color: green;")
            if ffmpeg_path and not self.ffmpeg_path_edit.text():
                self.ffmpeg_path_edit.setText(ffmpeg_path)
        else:
            self.ffmpeg_status_label.setText("❌ No encontrado")
            self.ffmpeg_status_label.setStyleSheet("color: red;")
    
    def apply_settings(self):
        """Aplica la configuración actual"""
        try:
            # Pestaña general
            theme_map = {0: "system", 1: "light", 2: "dark"}
            self.config.set("ui_theme", theme_map[self.theme_combo.currentIndex()])
            
            lang_map = {0: "es", 1: "en", 2: "auto"}
            self.config.set("ui_language", lang_map[self.lang_combo.currentIndex()])
            
            self.config.set("advanced_mode", self.advanced_check.isChecked())
            self.config.set("load_model_at_start", self.load_at_start_check.isChecked())
            self.config.set("normalize_audio", self.normalize_check.isChecked())
            self.config.set("confirm_exit", self.confirm_exit_check.isChecked())
            
            # Pestaña transcripción
            self.config.set("model_size", self.model_combo.currentText())
            self.config.set("fp16", self.fp16_check.isChecked())
            
            if self.default_lang_radio.isChecked():
                self.config.set("language", self.default_lang_combo.currentData())
            else:
                self.config.set("language", None)  # Detección automática
            
            self.config.set("use_vad", self.vad_check.isChecked())
            self.config.set("segment_large_files", self.segment_check.isChecked())
            self.config.set("max_segment_duration", self.segment_size_spin.value())
            
            # Pestaña exportación
            formats = []
            if self.txt_check.isChecked():
                formats.append("txt")
            if self.srt_check.isChecked():
                formats.append("srt")
            if self.vtt_check.isChecked():
                formats.append("vtt")
            
            self.config.set("export_formats", formats)
            self.config.set("auto_export", self.auto_export_check.isChecked())
            self.config.set("export_directory", self.export_dir_edit.text())
            
            # Opciones de formato
            self.config.set("max_chars_per_line", self.max_chars_spin.value())
            self.config.set("max_subtitle_duration", self.max_duration_spin.value())
            
            # Pestaña sistema
            self.config.set("ffmpeg_path", self.ffmpeg_path_edit.text())
            self.config.set("sample_rate", self.sample_rate_combo.currentData())
            self.config.set("channels", self.channels_combo.currentData())
            self.config.set("delete_temp_on_exit", self.delete_temp_check.isChecked())
            
            logger.info("Configuración aplicada")
            
        except Exception as e:
            logger.error(f"Error al aplicar configuración: {e}")
    
    def reset_settings(self):
        """Restablece configuración a valores predeterminados"""
        reply = QMessageBox.question(
            self,
            "Confirmar restablecimiento",
            "¿Estás seguro de que deseas restablecer todas las configuraciones a sus valores predeterminados?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.config.reset()
            self.load_config()
    
    def browse_export_dir(self):
        """Abre diálogo para seleccionar directorio de exportación"""
        current_dir = self.export_dir_edit.text()
        if not current_dir or not os.path.isdir(current_dir):
            current_dir = os.path.expanduser("~")
        
        directory = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar directorio de exportación",
            current_dir
        )
        
        if directory:
            self.export_dir_edit.setText(directory)
    
    def browse_ffmpeg(self):
        """Abre diálogo para seleccionar ejecutable de FFMPEG"""
        file_filter = "Ejecutables (*.exe)" if os.name == 'nt' else "Todos los archivos (*)"
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar ejecutable de FFMPEG",
            "",
            file_filter
        )
        
        if file_path:
            self.ffmpeg_path_edit.setText(file_path)
            self.check_ffmpeg()
    
    def clear_recent_files(self):
        """Limpia la lista de archivos recientes"""
        reply = QMessageBox.question(
            self,
            "Confirmar limpieza",
            "¿Estás seguro de que deseas eliminar todos los archivos recientes?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.config.set("recent_files", [])
            self.recent_list.clear()
    
    def clear_cache(self):
        """Limpia archivos de caché"""
        try:
            # Buscar archivos temporales de la aplicación
            temp_dir = tempfile.gettempdir()
            count = 0
            
            prefixes = ['whisper_', 'whisper-app_']
            
            # Crear diálogo de progreso
            progress = QProgressDialog("Limpiando archivos temporales...", "Cancelar", 0, 100, self)
            progress.setWindowTitle("Limpieza de caché")
            progress.setMinimumDuration(0)
            progress.setValue(0)
            
            # Contar archivos primero
            files_to_delete = []
            for file in os.listdir(temp_dir):
                if any(file.startswith(prefix) for prefix in prefixes):
                    file_path = os.path.join(temp_dir, file)
                    if os.path.isfile(file_path):
                        files_to_delete.append(file_path)
            
            total_files = len(files_to_delete)
            if total_files == 0:
                progress.close()
                QMessageBox.information(
                    self,
                    "Limpieza de caché",
                    "No se encontraron archivos temporales para limpiar."
                )
                return
            
            # Eliminar archivos
            for i, file_path in enumerate(files_to_delete):
                if progress.wasCanceled():
                    break
                
                try:
                    os.unlink(file_path)
                    count += 1
                except:
                    pass
                
                progress.setValue(int((i + 1) * 100 / total_files))
                QApplication.processEvents()
            
            progress.close()
            
            # Actualizar información
            self.update_cache_info()
            
            QMessageBox.information(
                self,
                "Caché limpiada",
                f"Se eliminaron {count} archivos temporales."
            )
            
        except Exception as e:
            logger.error(f"Error al limpiar caché: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Error al limpiar archivos temporales: {e}"
            )
    
    def show_advanced_options(self):
        """Muestra diálogo de opciones avanzadas"""
        dialog = AdvancedOptionsDialog(self.config, self)
        dialog.exec_()
    
    def accept(self):
        """Acción al aceptar el diálogo"""
        self.apply_settings()
        super().accept()


class AudioDeviceDialog(QDialog):
    """Diálogo para configurar dispositivos de audio"""
    
    def __init__(self, config_manager, recorder, parent=None):
        """
        Inicializa el diálogo de dispositivos de audio
        
        Args:
            config_manager: Instancia de ConfigManager
            recorder: Instancia de AudioRecorder
            parent: Widget padre
        """
        super().__init__(parent)
        self.config = config_manager
        self.recorder = recorder
        
        self.setWindowTitle("Dispositivos de Audio")
        self.resize(500, 400)
        
        self.setup_ui()
        self.load_devices()
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        layout = QVBoxLayout(self)
        
        # Dispositivos de entrada
        input_group = QGroupBox("Dispositivos de entrada")
        input_layout = QVBoxLayout(input_group)
        
        self.devices_list = QListWidget()
        input_layout.addWidget(self.devices_list)
        
        refresh_btn = QPushButton("Actualizar lista")
        refresh_btn.clicked.connect(self.load_devices)
        input_layout.addWidget(refresh_btn)
        
        layout.addWidget(input_group)
        
        # Parámetros de grabación
        params_group = QGroupBox("Parámetros de grabación")
        params_layout = QGridLayout(params_group)
        
        params_layout.addWidget(QLabel("Frecuencia de muestreo:"), 0, 0)
        self.sample_rate_combo = QComboBox()
        for rate in [8000, 16000, 22050, 44100, 48000]:
            self.sample_rate_combo.addItem(f"{rate} Hz", rate)
        # Preseleccionar 16000 (ideal para Whisper)
        index = self.sample_rate_combo.findData(self.config.get("sample_rate", 16000))
        self.sample_rate_combo.setCurrentIndex(max(0, index))
        params_layout.addWidget(self.sample_rate_combo, 0, 1)
        
        params_layout.addWidget(QLabel("Canales:"), 1, 0)
        self.channels_combo = QComboBox()
        self.channels_combo.addItem("Mono (1 canal)", 1)
        self.channels_combo.addItem("Estéreo (2 canales)", 2)
        self.channels_combo.setCurrentIndex(self.config.get("channels", 1) - 1)
        params_layout.addWidget(self.channels_combo, 1, 1)
        
        # Duración máxima de grabación
        params_layout.addWidget(QLabel("Tiempo máximo de grabación:"), 2, 0)
        self.max_recording_spin = QSpinBox()
        self.max_recording_spin.setRange(10, 3600)  # 10 segundos a 1 hora
        self.max_recording_spin.setValue(self.config.get("max_recording_time", 300))
        self.max_recording_spin.setSuffix(" segundos")
        params_layout.addWidget(self.max_recording_spin, 2, 1)
        
        layout.addWidget(params_group)
        
        # Visualización de nivel de audio
        level_group = QGroupBox("Nivel de audio")
        level_layout = QVBoxLayout(level_group)
        
        self.audio_level = QProgressBar()
        self.audio_level.setRange(0, 100)
        self.audio_level.setValue(0)
        level_layout.addWidget(self.audio_level)
        
        self.peak_label = QLabel("Nivel de pico: 0%")
        level_layout.addWidget(self.peak_label)
        
        layout.addWidget(level_group)
        
        # Test de grabación
        test_group = QGroupBox("Prueba de grabación")
        test_layout = QHBoxLayout(test_group)
        
        self.test_btn = QPushButton("Iniciar prueba")
        self.test_btn.clicked.connect(self.toggle_test_recording)
        test_layout.addWidget(self.test_btn)
        
        self.test_time_label = QLabel("00:00")
        test_layout.addWidget(self.test_time_label)
        
        self.play_test_btn = QPushButton("Reproducir prueba")
        self.play_test_btn.setEnabled(False)
        self.play_test_btn.clicked.connect(self.play_test_recording)
        test_layout.addWidget(self.play_test_btn)
        
        layout.addWidget(test_group)
        
        # Botones de diálogo
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        
        # Inicializar variables
        self.test_recording_path = None
        self.is_testing = False
        self.recording_time = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_recording_time)
        
        # Máximo nivel observado
        self.max_level = 0
    
    def load_devices(self):
        """Carga y muestra los dispositivos de audio disponibles"""
        self.devices_list.clear()
        
        try:
            devices = self.recorder.get_available_devices()
            
            if not devices:
                self.devices_list.addItem("No se encontraron dispositivos de entrada")
                return
            
            # Dispositivo actual
            current_device = self.config.get("audio_device")
            
            for device in devices:
                item = QListWidgetItem(f"{device['name']} ({device['channels']} canales)")
                item.setData(Qt.UserRole, device['id'])
                
                if device['default']:
                    item.setText(f"{item.text()} [Predeterminado]")
                
                if current_device is not None and device['id'] == current_device:
                    item.setText(f"{item.text()} [Seleccionado]")
                    self.devices_list.setCurrentItem(item)
                elif current_device is None and device['default']:
                    self.devices_list.setCurrentItem(item)
                
                self.devices_list.addItem(item)
        
        except Exception as e:
            logger.error(f"Error al cargar dispositivos: {e}")
            self.devices_list.addItem(f"Error al cargar dispositivos: {e}")
    
    def update_recording_time(self):
        """Actualiza el tiempo mostrado durante la grabación de prueba"""
        if self.is_testing:
            self.recording_time += 1
            minutes = self.recording_time // 60
            seconds = self.recording_time % 60
            self.test_time_label.setText(f"{minutes:02d}:{seconds:02d}")
    
    def toggle_test_recording(self):
        """Inicia o detiene una prueba de grabación"""
        if not self.is_testing:
            # Iniciar grabación de prueba
            selected_items = self.devices_list.selectedItems()
            if not selected_items:
                QMessageBox.warning(
                    self,
                    "Selección requerida",
                    "Selecciona un dispositivo para la prueba"
                )
                return
            
            device_id = selected_items[0].data(Qt.UserRole)
            
            # Configurar parámetros
            sample_rate = self.sample_rate_combo.currentData()
            channels = self.channels_combo.currentData()
            
            # Iniciar prueba
            self.recorder.set_device(device_id)
            self.recorder.set_parameters(sample_rate, channels)
            
            # Reiniciar nivel máximo
            self.max_level = 0
            
            if not self.recorder.start_recording():
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se pudo iniciar la grabación de prueba"
                )
                return
            
            # Conectar señales
            self.recorder.signals.recording_level.connect(self.update_audio_level)
            
            # Iniciar timer
            self.recording_time = 0
            self.test_time_label.setText("00:00")
            self.timer.start(1000)
            
            self.is_testing = True
            self.test_btn.setText("Detener prueba")
            self.play_test_btn.setEnabled(False)
            
        else:
            # Detener grabación
            self.timer.stop()
            self.test_recording_path = self.recorder.stop_recording()
            
            # Desconectar señal
            self.recorder.signals.recording_level.disconnect(self.update_audio_level)
            
            self.is_testing = False
            self.test_btn.setText("Iniciar prueba")
            
            # Habilitar reproducción si hay archivo
            if self.test_recording_path and os.path.exists(self.test_recording_path):
                self.play_test_btn.setEnabled(True)
    
    def update_audio_level(self, level):
        """Actualiza el indicador de nivel de audio"""
        level_percent = min(int(level * 100), 100)
        self.audio_level.setValue(level_percent)
        
        # Actualizar nivel máximo
        if level_percent > self.max_level:
            self.max_level = level_percent
            self.peak_label.setText(f"Nivel de pico: {self.max_level}%")
    
    def play_test_recording(self):
        """Reproduce la grabación de prueba"""
        if not self.test_recording_path or not os.path.exists(self.test_recording_path):
            QMessageBox.warning(
                self,
                "Error",
                "No hay grabación disponible para reproducir"
            )
            return
        
        try:
            # Usar reproductor predeterminado del sistema
            if sys.platform == 'win32':
                os.startfile(self.test_recording_path)
            elif sys.platform == 'darwin':  # macOS
                subprocess.call(['open', self.test_recording_path])
            else:  # Linux y otros
                subprocess.call(['xdg-open', self.test_recording_path])
                
        except Exception as e:
            logger.error(f"Error al reproducir grabación: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo reproducir la grabación: {e}"
            )
    
    def accept(self):
        """Guarda configuración y cierra diálogo"""
        # Verificar si hay grabación en curso
        if self.is_testing:
            self.toggle_test_recording()
        
        # Guardar dispositivo seleccionado
        selected_items = self.devices_list.selectedItems()
        if selected_items:
            device_id = selected_items[0].data(Qt.UserRole)
            self.config.set("audio_device", device_id)
        
        # Guardar parámetros
        self.config.set("sample_rate", self.sample_rate_combo.currentData())
        self.config.set("channels", self.channels_combo.currentData())
        self.config.set("max_recording_time", self.max_recording_spin.value())
        
        # Limpiar archivo de prueba
        if self.test_recording_path and os.path.exists(self.test_recording_path):
            try:
                os.unlink(self.test_recording_path)
            except:
                pass
        
        super().accept()
    
    def reject(self):
        """Cancela diálogo"""
        # Verificar si hay grabación en curso
        if self.is_testing:
            self.toggle_test_recording()
        
        # Limpiar archivo de prueba
        if self.test_recording_path and os.path.exists(self.test_recording_path):
            try:
                os.unlink(self.test_recording_path)
            except:
                pass
        
        super().reject()


class AdvancedOptionsDialog(QDialog):
    """Diálogo de opciones avanzadas para Whisper"""
    
    def __init__(self, config_manager, parent=None):
        """
        Inicializa el diálogo de opciones avanzadas
        
        Args:
            config_manager: Instancia de ConfigManager
            parent: Widget padre
        """
        super().__init__(parent)
        self.config = config_manager
        
        self.setWindowTitle("Opciones Avanzadas")
        self.resize(550, 450)
        
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        layout = QVBoxLayout(self)
        
        # Nota informativa
        info_label = QLabel(
            "⚠️ <b>Aviso:</b> Estas opciones son para usuarios avanzados. "
            "Modificarlas puede afectar el rendimiento y la calidad de las transcripciones."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Pestañas para organizar opciones
        tabs = QTabWidget()
        
        # Pestaña de decodificación
        decode_tab = QWidget()
        self.setup_decode_tab(decode_tab)
        tabs.addTab(decode_tab, "Decodificación")
        
        # Pestaña de procesamiento
        process_tab = QWidget()
        self.setup_process_tab(process_tab)
        tabs.addTab(process_tab, "Procesamiento")
        
        # Pestaña de rendimiento
        perf_tab = QWidget()
        self.setup_perf_tab(perf_tab)
        tabs.addTab(perf_tab, "Rendimiento")
        
        layout.addWidget(tabs)
        
        # Botones de diálogo
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Reset)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Reset).clicked.connect(self.reset_values)
        
        layout.addWidget(button_box)
    
    def setup_decode_tab(self, tab):
        """Configura pestaña de opciones de decodificación"""
        layout = QVBoxLayout(tab)
        
        # Parámetros de búsqueda de beam
        beam_group = QGroupBox("Búsqueda de beam")
        beam_layout = QFormLayout(beam_group)
        
        self.beam_size_spin = QSpinBox()
        self.beam_size_spin.setRange(1, 10)
        self.beam_size_spin.setValue(5)
        self.beam_size_spin.setToolTip(
            "Número de beams en búsqueda de beam. A mayor valor, resultados más precisos pero más lentos."
        )
        beam_layout.addRow("Tamaño de beam:", self.beam_size_spin)
        
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 1.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(0.0)
        self.temperature_spin.setToolTip(
            "Temperatura para muestreo. 0 = determinístico, mayor valor = más aleatorio."
        )
        beam_layout.addRow("Temperatura:", self.temperature_spin)
        
        self.best_of_spin = QSpinBox()
        self.best_of_spin.setRange(1, 10)
        self.best_of_spin.setValue(5)
        self.best_of_spin.setToolTip(
            "Número de candidatos al muestrear con temperatura no cero."
        )
        beam_layout.addRow("Best of:", self.best_of_spin)
        
        layout.addWidget(beam_group)
        
        # Parámetros de prompt
        prompt_group = QGroupBox("Prompt inicial")
        prompt_layout = QVBoxLayout(prompt_group)
        
        self.use_prompt_check = QCheckBox("Usar prompt inicial")
        self.use_prompt_check.setToolTip("Proporciona un contexto inicial para la transcripción")
        prompt_layout.addWidget(self.use_prompt_check)
        
        self.prompt_text = QTextEdit()
        self.prompt_text.setPlaceholderText("Ingresa texto de prompt inicial aquí...")
        self.prompt_text.setEnabled(False)
        prompt_layout.addWidget(self.prompt_text)
        
        self.use_prompt_check.toggled.connect(self.prompt_text.setEnabled)
        
        layout.addWidget(prompt_group)
        
        # Filtrado de tokens
        tokens_group = QGroupBox("Filtrado de tokens")
        tokens_layout = QVBoxLayout(tokens_group)
        
        self.no_speech_check = QCheckBox("Suprimir tokens con probabilidad de no-voz")
        self.no_speech_check.setToolTip("Reduce el texto que no corresponde a voz real")
        tokens_layout.addWidget(self.no_speech_check)
        
        layout.addWidget(tokens_group)
        
        layout.addStretch()
    
    def setup_process_tab(self, tab):
        """Configura pestaña de opciones de procesamiento"""
        layout = QVBoxLayout(tab)
        
        # Detección de voz (VAD)
        vad_group = QGroupBox("Detección de actividad de voz (VAD)")
        vad_layout = QVBoxLayout(vad_group)
        
        self.vad_check = QCheckBox("Usar detección de voz")
        self.vad_check.setToolTip("Filtrar partes sin voz del audio")
        vad_layout.addWidget(self.vad_check)
        
        # Parámetros de VAD
        vad_params_layout = QFormLayout()
        
        self.vad_threshold_spin = QDoubleSpinBox()
        self.vad_threshold_spin.setRange(0.01, 0.99)
        self.vad_threshold_spin.setSingleStep(0.05)
        self.vad_threshold_spin.setValue(0.5)
        self.vad_threshold_spin.setToolTip("Umbral para detección de voz (menor = más sensible)")
        vad_params_layout.addRow("Umbral de detección:", self.vad_threshold_spin)
        
        self.vad_min_speech_spin = QDoubleSpinBox()
        self.vad_min_speech_spin.setRange(0.1, 5.0)
        self.vad_min_speech_spin.setSingleStep(0.1)
        self.vad_min_speech_spin.setValue(0.5)
        self.vad_min_speech_spin.setSuffix(" segundos")
        self.vad_min_speech_spin.setToolTip("Duración mínima de segmentos de voz")
        vad_params_layout.addRow("Mínimo de voz:", self.vad_min_speech_spin)
        
        self.vad_min_silence_spin = QDoubleSpinBox()
        self.vad_min_silence_spin.setRange(0.1, 5.0)
        self.vad_min_silence_spin.setSingleStep(0.1)
        self.vad_min_silence_spin.setValue(0.5)
        self.vad_min_silence_spin.setSuffix(" segundos")
        self.vad_min_silence_spin.setToolTip("Duración mínima de silencio para separar segmentos")
        vad_params_layout.addRow("Mínimo de silencio:", self.vad_min_silence_spin)
        
        vad_layout.addLayout(vad_params_layout)
        
        layout.addWidget(vad_group)
        
        # Segmentación
        segment_group = QGroupBox("Segmentación de archivos grandes")
        segment_layout = QVBoxLayout(segment_group)
        
        self.segment_check = QCheckBox("Segmentar archivos grandes")
        self.segment_check.setToolTip("Divide archivos grandes en segmentos para procesamiento")
        segment_layout.addWidget(self.segment_check)
        
        segment_params_layout = QFormLayout()
        
        self.segment_duration_spin = QSpinBox()
        self.segment_duration_spin.setRange(30, 1800)
        self.segment_duration_spin.setValue(600)
        self.segment_duration_spin.setSuffix(" segundos")
        self.segment_duration_spin.setToolTip("Duración máxima de cada segmento")
        segment_params_layout.addRow("Duración de segmento:", self.segment_duration_spin)
        
        self.segment_overlap_spin = QDoubleSpinBox()
        self.segment_overlap_spin.setRange(0.0, 30.0)
        self.segment_overlap_spin.setSingleStep(0.5)
        self.segment_overlap_spin.setValue(1.0)
        self.segment_overlap_spin.setSuffix(" segundos")
        self.segment_overlap_spin.setToolTip("Superposición entre segmentos para continuidad")
        segment_params_layout.addRow("Superposición:", self.segment_overlap_spin)
        
        segment_layout.addLayout(segment_params_layout)
        
        layout.addWidget(segment_group)
        
        # Normalización
        norm_group = QGroupBox("Normalización de audio")
        norm_layout = QVBoxLayout(norm_group)
        
        self.normalize_check = QCheckBox("Normalizar audio antes de transcribir")
        self.normalize_check.setToolTip("Ajusta el volumen del audio para mejor transcripción")
        norm_layout.addWidget(self.normalize_check)
        
        layout.addWidget(norm_group)
        
        layout.addStretch()
    
    def setup_perf_tab(self, tab):
        """Configura pestaña de opciones de rendimiento"""
        layout = QVBoxLayout(tab)
        
        # Opciones de precisión
        precision_group = QGroupBox("Precisión")
        precision_layout = QVBoxLayout(precision_group)
        
        self.fp16_check = QCheckBox("Usar FP16 (media precisión)")
        self.fp16_check.setToolTip("Ahorra memoria pero puede reducir ligeramente la precisión")
        precision_layout.addWidget(self.fp16_check)
        
        layout.addWidget(precision_group)
        
        # Opciones de dispositivo
        device_group = QGroupBox("Dispositivo de cómputo")
        device_layout = QVBoxLayout(device_group)
        
        self.device_radio_cpu = QRadioButton("CPU")
        self.device_radio_gpu = QRadioButton("GPU (CUDA/ROCm)")
        
        device_layout.addWidget(self.device_radio_cpu)
        device_layout.addWidget(self.device_radio_gpu)
        
        # Verificar disponibilidad de GPU
        import torch
        has_cuda = torch.cuda.is_available()
        
        # Deshabilitar GPU si no está disponible
        if not has_cuda:
            self.device_radio_gpu.setEnabled(False)
            self.device_radio_gpu.setText("GPU (no disponible)")
            self.device_radio_cpu.setChecked(True)
        else:
            # Mostrar información de GPU
            gpu_info = QLabel(f"GPU detectada: {torch.cuda.get_device_name(0)}")
            device_layout.addWidget(gpu_info)
        
        layout.addWidget(device_group)
        
        # Opciones de multithreading
        thread_group = QGroupBox("Multithreading")
        thread_layout = QFormLayout(thread_group)
        
        self.num_threads_spin = QSpinBox()
        self.num_threads_spin.setRange(1, 16)
        self.num_threads_spin.setValue(4)
        thread_layout.addRow("Número de hilos:", self.num_threads_spin)
        
        layout.addWidget(thread_group)
        
        # Opciones de caché de modelos
        cache_group = QGroupBox("Caché de modelos")
        cache_layout = QVBoxLayout(cache_group)
        
        self.cache_check = QCheckBox("Usar caché de modelos")
        self.cache_check.setToolTip("Almacena modelos descargados para uso futuro")
        cache_layout.addWidget(self.cache_check)
        
        cache_dir_layout = QHBoxLayout()
        cache_dir_layout.addWidget(QLabel("Directorio de caché:"))
        
        self.cache_dir_edit = QLineEdit()
        self.cache_dir_edit.setReadOnly(True)
        cache_dir_layout.addWidget(self.cache_dir_edit, 1)
        
        self.browse_cache_btn = QPushButton("Examinar...")
        self.browse_cache_btn.clicked.connect(self.browse_cache_dir)
        cache_dir_layout.addWidget(self.browse_cache_btn)
        
        cache_layout.addLayout(cache_dir_layout)
        
        layout.addWidget(cache_group)
        
        layout.addStretch()
    
    def browse_cache_dir(self):
        """Abre diálogo para seleccionar directorio de caché"""
        current_dir = self.cache_dir_edit.text()
        if not current_dir or not os.path.isdir(current_dir):
            current_dir = os.path.expanduser("~")
        
        directory = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar directorio de caché de modelos",
            current_dir
        )
        
        if directory:
            self.cache_dir_edit.setText(directory)
    
    def load_config(self):
        """Carga la configuración actual"""
        try:
            # Pestaña de decodificación
            self.beam_size_spin.setValue(self.config.get("beam_size", 5))
            self.temperature_spin.setValue(self.config.get("temperature", 0.0))
            self.best_of_spin.setValue(self.config.get("best_of", 5))
            
            prompt = self.config.get("initial_prompt", "")
            self.use_prompt_check.setChecked(bool(prompt))
            self.prompt_text.setPlainText(prompt)
            self.prompt_text.setEnabled(bool(prompt))
            
            self.no_speech_check.setChecked(self.config.get("suppress_tokens_no_speech", False))
            
            # Pestaña de procesamiento
            self.vad_check.setChecked(self.config.get("use_vad", False))
            self.vad_threshold_spin.setValue(self.config.get("vad_threshold", 0.5))
            self.vad_min_speech_spin.setValue(self.config.get("vad_min_speech", 0.5))
            self.vad_min_silence_spin.setValue(self.config.get("vad_min_silence", 0.5))
            
            self.segment_check.setChecked(self.config.get("segment_large_files", True))
            self.segment_duration_spin.setValue(self.config.get("max_segment_duration", 600))
            self.segment_overlap_spin.setValue(self.config.get("segment_overlap", 1.0))
            
            self.normalize_check.setChecked(self.config.get("normalize_audio", False))
            
            # Pestaña de rendimiento
            self.fp16_check.setChecked(self.config.get("fp16", True))
            
            device = self.config.get("device", "cpu")
            if device == "cuda" and self.device_radio_gpu.isEnabled():
                self.device_radio_gpu.setChecked(True)
            else:
                self.device_radio_cpu.setChecked(True)
            
            self.num_threads_spin.setValue(self.config.get("num_threads", 4))
            
            self.cache_check.setChecked(self.config.get("use_model_cache", True))
            self.cache_dir_edit.setText(self.config.get("model_cache_dir", ""))
            
        except Exception as e:
            logger.error(f"Error al cargar configuración avanzada: {e}")
    
    def reset_values(self):
        """Restablece valores predeterminados"""
        # Pestaña de decodificación
        self.beam_size_spin.setValue(5)
        self.temperature_spin.setValue(0.0)
        self.best_of_spin.setValue(5)
        self.use_prompt_check.setChecked(False)
        self.prompt_text.setPlainText("")
        self.prompt_text.setEnabled(False)
        self.no_speech_check.setChecked(False)
        
        # Pestaña de procesamiento
        self.vad_check.setChecked(False)
        self.vad_threshold_spin.setValue(0.5)
        self.vad_min_speech_spin.setValue(0.5)
        self.vad_min_silence_spin.setValue(0.5)
        self.segment_check.setChecked(True)
        self.segment_duration_spin.setValue(600)
        self.segment_overlap_spin.setValue(1.0)
        self.normalize_check.setChecked(False)
        
        # Pestaña de rendimiento
        self.fp16_check.setChecked(True)
        self.device_radio_cpu.setChecked(True)
        self.num_threads_spin.setValue(4)
        self.cache_check.setChecked(True)
        self.cache_dir_edit.setText("")
    
    def accept(self):
        """Guarda configuración y cierra diálogo"""
        try:
            # Pestaña de decodificación
            self.config.set("beam_size", self.beam_size_spin.value())
            self.config.set("temperature", self.temperature_spin.value())
            self.config.set("best_of", self.best_of_spin.value())
            
            if self.use_prompt_check.isChecked():
                self.config.set("initial_prompt", self.prompt_text.toPlainText())
            else:
                self.config.set("initial_prompt", "")
                
            self.config.set("suppress_tokens_no_speech", self.no_speech_check.isChecked())
            
            # Pestaña de procesamiento
            self.config.set("use_vad", self.vad_check.isChecked())
            self.config.set("vad_threshold", self.vad_threshold_spin.value())
            self.config.set("vad_min_speech", self.vad_min_speech_spin.value())
            self.config.set("vad_min_silence", self.vad_min_silence_spin.value())
            
            self.config.set("segment_large_files", self.segment_check.isChecked())
            self.config.set("max_segment_duration", self.segment_duration_spin.value())
            self.config.set("segment_overlap", self.segment_overlap_spin.value())
            
            self.config.set("normalize_audio", self.normalize_check.isChecked())
            
            # Pestaña de rendimiento
            self.config.set("fp16", self.fp16_check.isChecked())
            
            if self.device_radio_gpu.isChecked() and self.device_radio_gpu.isEnabled():
                self.config.set("device", "cuda")
            else:
                self.config.set("device", "cpu")
                
            self.config.set("num_threads", self.num_threads_spin.value())
            
            self.config.set("use_model_cache", self.cache_check.isChecked())
            self.config.set("model_cache_dir", self.cache_dir_edit.text())
            
        except Exception as e:
            logger.error(f"Error al guardar configuración avanzada: {e}")
        
        super().accept()


class AboutDialog(QDialog):
    """Diálogo 'Acerca de'"""
    
    def __init__(self, parent=None):
        """
        Inicializa el diálogo 'Acerca de'
        
        Args:
            parent: Widget padre
        """
        super().__init__(parent)
        
        self.setWindowTitle("Acerca de WhisperApp")
        self.setFixedSize(450, 420)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Logo (placeholder)
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        # Logo simulado (crea un texto estilizado)
        font = QFont("Arial", 28, QFont.Bold)
        logo_label.setFont(font)
        logo_label.setText("🎤 WhisperApp")
        logo_label.setStyleSheet("color: #3366CC;")
        layout.addWidget(logo_label)
        
        # Versión
        version_label = QLabel("Versión 1.0.0")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        # Línea separadora
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # Descripción
        desc_label = QLabel(
            "<p>Aplicación para transcripción de audio y video "
            "utilizando el modelo Whisper de OpenAI.</p>"
            "<p>Whisper es un sistema de reconocimiento de voz de código abierto "
            "entrenado en grandes cantidades de datos de audio y texto. "
            "Ofrece precisión cercana a la humana y soporte para múltiples idiomas.</p>"
        )
        desc_label.setWordWrap(True)
        desc_label.setTextFormat(Qt.RichText)
        desc_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(desc_label)
        
        # Características
        features_label = QLabel(
            "<b>Características principales:</b>"
            "<ul>"
            "<li>Transcripción de audio/video con alta precisión</li>"
            "<li>Soporte para múltiples idiomas</li>"
            "<li>Traducción de audio a texto en otro idioma</li>"
            "<li>Exportación en formatos TXT, SRT y VTT</li>"
            "<li>Grabación directa desde micrófono</li>"
            "</ul>"
        )
        features_label.setWordWrap(True)
        features_label.setTextFormat(Qt.RichText)
        layout.addWidget(features_label)
        
        # Créditos
        credits_label = QLabel(
            "<p><b>Desarrollado con:</b> Python, PyQt5, OpenAI Whisper</p>"
            "<p>© 2023 Todos los derechos reservados.</p>"
        )
        credits_label.setWordWrap(True)
        credits_label.setTextFormat(Qt.RichText)
        credits_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(credits_label)
        
        # Enlaces
        links_layout = QHBoxLayout()
        
        whisper_link = QLabel("<a href='https://github.com/openai/whisper'>OpenAI Whisper</a>")
        whisper_link.setOpenExternalLinks(True)
        whisper_link.setAlignment(Qt.AlignCenter)
        links_layout.addWidget(whisper_link)
        
        pyqt_link = QLabel("<a href='https://www.riverbankcomputing.com/software/pyqt/'>PyQt</a>")
        pyqt_link.setOpenExternalLinks(True)
        pyqt_link.setAlignment(Qt.AlignCenter)
        links_layout.addWidget(pyqt_link)
        
        layout.addLayout(links_layout)
        
        # Botones
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)


class ErrorReportDialog(QDialog):
    """Diálogo para reportar errores"""
    
    def __init__(self, error_msg, trace=None, parent=None):
        """
        Inicializa el diálogo de reporte de errores
        
        Args:
            error_msg (str): Mensaje de error
            trace (str): Traza completa del error
            parent: Widget padre
        """
        super().__init__(parent)
        
        self.setWindowTitle("Error")
        self.resize(600, 400)
        
        self.error_msg = error_msg
        self.trace = trace
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        layout = QVBoxLayout(self)
        
        # Icono de error
        icon_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(self.style().standardIcon(QStyle.SP_MessageBoxCritical).pixmap(48, 48))
        icon_layout.addWidget(icon_label)
        
        # Mensaje de error
        error_label = QLabel(self.error_msg)
        error_label.setWordWrap(True)
        error_label.setTextFormat(Qt.RichText)
        font = error_label.font()
        font.setBold(True)
        error_label.setFont(font)
        icon_layout.addWidget(error_label, 1)
        
        layout.addLayout(icon_layout)
        
        if self.trace:
            # Detalles técnicos
            details_group = QGroupBox("Detalles técnicos")
            details_layout = QVBoxLayout(details_group)
            
            trace_text = QTextEdit()
            trace_text.setReadOnly(True)
            trace_text.setLineWrapMode(QTextEdit.NoWrap)
            trace_text.setPlainText(self.trace)
            
            details_layout.addWidget(trace_text)
            
            # Botón para copiar
            copy_btn = QPushButton("Copiar al portapapeles")
            copy_btn.clicked.connect(lambda: self.copy_to_clipboard(self.trace))
            details_layout.addWidget(copy_btn)
            
            layout.addWidget(details_group)
        
        # Acciones sugeridas
        actions_label = QLabel(
            "<b>Acciones sugeridas:</b>"
            "<ul>"
            "<li>Verifica que FFMPEG esté instalado y en el PATH</li>"
            "<li>Asegúrate de tener suficiente espacio en disco y memoria</li>"
            "<li>Comprueba que el archivo de audio/video sea válido</li>"
            "<li>Reinicia la aplicación e intenta nuevamente</li>"
            "</ul>"
        )
        actions_label.setWordWrap(True)
        actions_label.setTextFormat(Qt.RichText)
        layout.addWidget(actions_label)
        
        # Botones
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
    
    def copy_to_clipboard(self, text):
        """Copia texto al portapapeles"""
        QApplication.clipboard().setText(text)
        
        # Mostrar confirmación brevemente
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setText("Copiado al portapapeles")
        msg.setStandardButtons(QMessageBox.NoButton)
        msg.show()
        
        # Cerrar automáticamente después de 1.5 segundos
        QTimer.singleShot(1500, msg.close)


class ModelDownloadDialog(QDialog):
    """Diálogo para gestionar la descarga de modelos"""
    
    # Señales para comunicación con el hilo de descarga
    download_progress = pyqtSignal(int, str)
    download_complete = pyqtSignal(str)
    download_error = pyqtSignal(str)
    
    def __init__(self, model_name, parent=None):
        """
        Inicializa el diálogo de descarga de modelos
        
        Args:
            model_name (str): Nombre del modelo a descargar
            parent: Widget padre
        """
        super().__init__(parent)
        
        self.model_name = model_name
        self.download_path = ""
        
        self.setWindowTitle(f"Descargando modelo {model_name}")
        self.setFixedSize(400, 200)
        self.setModal(True)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configura la interfaz del diálogo"""
        layout = QVBoxLayout(self)
        
        # Información
        info_label = QLabel(f"Descargando modelo Whisper <b>{self.model_name}</b>")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        # Tamaños aproximados
        sizes = {
            "tiny": "75 MB",
            "base": "150 MB",
            "small": "500 MB",
            "medium": "1.5 GB",
            "large": "3 GB"
        }
        
        size_label = QLabel(f"Tamaño aproximado: {sizes.get(self.model_name, 'Desconocido')}")
        size_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(size_label)
        
        # Progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Estado
        self.status_label = QLabel("Iniciando descarga...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Botones
        button_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        button_box.rejected.connect(self.cancel_download)
        layout.addWidget(button_box)
        
        # Variable para seguimiento de cancelación
        self.cancelled = False
    
    def start_download(self):
        """Inicia la descarga del modelo"""
        # La descarga real se maneja dentro de Whisper
        # Este diálogo simula el progreso
        
        # Actualizar cada 0.5 segundos
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.current_progress = 0
        self.timer.start(500)
    
    def update_progress(self):
        """Actualiza el progreso de la descarga simulada"""
        if self.cancelled:
            return
        
        # Simular progreso
        if self.current_progress < 95:
            # Incremento variable para simular velocidad de descarga
            increment = 5 if self.current_progress < 50 else 2
            self.current_progress += increment
            
            # Actualizar barra y etiqueta
            self.progress_bar.setValue(self.current_progress)
            
            # Mensajes según el progreso
            if self.current_progress < 30:
                self.status_label.setText("Descargando archivos del modelo...")
            elif self.current_progress < 60:
                self.status_label.setText("Recibiendo datos...")
            elif self.current_progress < 90:
                self.status_label.setText("Verificando integridad...")
            else:
                self.status_label.setText("Finalizando descarga...")
        else:
            # Simular finalización
            self.current_progress = 100
            self.progress_bar.setValue(100)
            self.status_label.setText("¡Descarga completada!")
            self.timer.stop()
            
            # Simular descarga completada después de un breve retraso
            QTimer.singleShot(1000, self.complete_download)
    
    def complete_download(self):
        """Simula la finalización de la descarga"""
        self.accept()
    
    def cancel_download(self):
        """Cancela la descarga del modelo"""
        self.cancelled = True
        self.timer.stop()
        self.reject()