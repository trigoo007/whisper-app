#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ventana principal de WhisperApp
"""

import os
import logging
import tempfile
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QComboBox, QListWidget, QListWidgetItem,
    QProgressBar, QTextEdit, QMessageBox, QFileDialog, QAction,
    QMenu, QStatusBar, QToolBar, QCheckBox, QShortcut, QApplication
)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSlot, pyqtSignal, QObject
from PyQt5.QtGui import QIcon, QTextCursor, QKeySequence

from whisper_app.core.transcriber import Transcriber
from whisper_app.core.recorder import AudioRecorder
from whisper_app.core.file_manager import FileManager
from whisper_app.ui.dialogs import (
    ConfigDialog, 
    AudioDeviceDialog, 
    AdvancedOptionsDialog, 
    AboutDialog,
    ModelDownloadDialog,
    get_ffmpeg_install_instructions
)
from whisper_app.utils.ffmpeg_utils import verify_ffmpeg, verify_ffmpeg_components
from whisper_app.utils.text_utils import extract_keywords
from whisper_app.utils.language_data import get_stopwords
from whisper_app.core.realtime_transcriber import RealtimeTranscriber

from whisper_app.utils.dependencies import import_optional
psutil = import_optional("psutil")

logger = logging.getLogger(__name__)

class TranscriptionThread(QThread):
    """Hilo para ejecutar la transcripción en segundo plano"""
    
    def __init__(self, transcriber, file_info, language, translate_to):
        super().__init__()
        self.transcriber = transcriber
        self.file_info = file_info
        self.language = language
        self.translate_to = translate_to
    
    def run(self):
        """Ejecuta la transcripción"""
        self.transcriber.transcribe_file(
            self.file_info['processed_path'],
            self.language,
            self.translate_to
        )

class ModelLoaderThread(QThread):
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(int, str)

    def __init__(self, transcriber, model_name):
        super().__init__()
        self.transcriber = transcriber
        self.model_name = model_name

    def run(self):
        # Conectar señales de progreso
        self.transcriber.signals.progress.connect(self.progress.emit)
        success = self.transcriber.load_model(self.model_name)
        self.finished.emit(success, self.model_name)

class ImportWorker(QThread):
    finished = pyqtSignal(dict, str, bool, str)  # file_info, file_path, is_recording, error
    def __init__(self, file_manager, file_path, normalize, is_recording):
        super().__init__()
        self.file_manager = file_manager
        self.file_path = file_path
        self.normalize = normalize
        self.is_recording = is_recording
        self.error = None
        self.file_info = None
    def run(self):
        try:
            self.file_info = self.file_manager.import_file(self.file_path, self.normalize)
        except Exception as e:
            self.error = str(e)
        self.finished.emit(self.file_info, self.file_path, self.is_recording, self.error)

class ExportWorker(QThread):
    finished = pyqtSignal(dict, str, list, str)  # exported, file_path, formats, error
    def __init__(self, file_manager, transcription, file_path, formats):
        super().__init__()
        self.file_manager = file_manager
        self.transcription = transcription
        self.file_path = file_path
        self.formats = formats
        self.exported = None
        self.error = None
    def run(self):
        try:
            self.exported = self.file_manager.export_transcription(self.transcription, self.file_path, self.formats)
        except Exception as e:
            self.error = str(e)
        self.finished.emit(self.exported, self.file_path, self.formats, self.error)

class MainWindow(QMainWindow):
    """Ventana principal de la aplicación"""
    
    def __init__(self, config_manager):
        """
        Inicializa la ventana principal
        
        Args:
            config_manager: Instancia de ConfigManager
        """
        super().__init__()
        self.config = config_manager
        
        # Inicializar componentes principales
        self.transcriber = Transcriber(self.config)
        self.recorder = AudioRecorder(self.config)
        self.file_manager = FileManager(self.config)
        
        # Estado de la aplicación
        self.transcription_thread = None
        self.files = {}  # {name: file_info}
        self.results = {}  # {name: transcription_result}
        self.current_file = None
        self.original_text = ""  # Para edición
        
        # Configurar UI
        self.setup_ui()
        self.setup_signals()
        self.setup_shortcuts()
        
        # Configuración inicial
        self.setWindowTitle("WhisperApp - Transcripción de Audio/Video")
        self.resize(1000, 700)
        self.statusBar().showMessage("Listo")
        
        logger.info("Ventana principal inicializada")
    
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        # Crear menús
        self.setup_menus()
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Panel superior - Modelo
        model_panel = QHBoxLayout()
        model_panel.addWidget(QLabel("Modelo:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        # Establecer modelo predeterminado de la configuración
        default_model = self.config.get("model_size", "base")
        idx = self.model_combo.findText(default_model)
        self.model_combo.setCurrentIndex(max(0, idx))
        model_panel.addWidget(self.model_combo)
        
        self.load_model_btn = QPushButton("Cargar Modelo")
        model_panel.addWidget(self.load_model_btn)
        
        model_panel.addStretch()
        main_layout.addLayout(model_panel)
        
        # Panel de idioma
        lang_panel = QHBoxLayout()
        lang_panel.addWidget(QLabel("Idioma:"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("Detectar automáticamente", None)
        
        # Agregar idiomas soportados
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
            self.language_combo.addItem(name, code)
        
        lang_panel.addWidget(self.language_combo)
        
        lang_panel.addWidget(QLabel("Traducir a:"))
        self.translate_combo = QComboBox()
        self.translate_combo.addItem("No traducir", None)
        for name, code in languages:
            self.translate_combo.addItem(name, code)
        
        lang_panel.addWidget(self.translate_combo)
        lang_panel.addStretch()
        main_layout.addLayout(lang_panel)
        
        # Botones principales
        btn_panel = QHBoxLayout()
        
        self.import_btn = QPushButton("Importar Audio/Video")
        btn_panel.addWidget(self.import_btn)
        
        self.record_btn = QPushButton("Grabar Micrófono")
        btn_panel.addWidget(self.record_btn)
        
        self.transcribe_btn = QPushButton("Transcribir")
        self.transcribe_btn.setEnabled(False)
        btn_panel.addWidget(self.transcribe_btn)
        
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.setEnabled(False)
        btn_panel.addWidget(self.cancel_btn)
        
        main_layout.addLayout(btn_panel)
        
        # Barra de progreso
        progress_layout = QHBoxLayout()
        
        self.time_label = QLabel("00:00")
        progress_layout.addWidget(self.time_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar, 1)
        
        main_layout.addLayout(progress_layout)
        
        # Estado del proceso
        self.status_label = QLabel("Listo para usar")
        main_layout.addWidget(self.status_label)
        
        # Panel principal (dividido)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, 1)  # stretch = 1
        
        # Panel izquierdo - Lista de archivos
        files_widget = QWidget()
        files_layout = QVBoxLayout(files_widget)
        files_layout.setContentsMargins(0, 0, 0, 0)
        
        files_layout.addWidget(QLabel("Archivos:"))
        
        self.files_list = QListWidget()
        self.files_list.setContextMenuPolicy(Qt.CustomContextMenu)
        files_layout.addWidget(self.files_list)
        
        splitter.addWidget(files_widget)
        
        # Panel derecho - Transcripción
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        # Información
        self.info_label = QLabel()
        self.info_label.setTextFormat(Qt.RichText)
        self.info_label.setWordWrap(True)
        self.info_label.setFrameStyle(QLabel.StyledPanel | QLabel.Sunken)
        self.info_label.setMinimumHeight(80)
        text_layout.addWidget(self.info_label)
        
        # Editor de texto
        text_layout.addWidget(QLabel("Transcripción:"))
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        text_layout.addWidget(self.text_edit)
        
        # Controles de edición
        edit_panel = QHBoxLayout()
        
        self.edit_btn = QPushButton("Editar Transcripción")
        self.edit_btn.setEnabled(False)
        edit_panel.addWidget(self.edit_btn)
        
        self.save_edit_btn = QPushButton("Aplicar Cambios")
        self.save_edit_btn.setEnabled(False)
        edit_panel.addWidget(self.save_edit_btn)
        
        self.cancel_edit_btn = QPushButton("Cancelar Edición")
        self.cancel_edit_btn.setEnabled(False)
        edit_panel.addWidget(self.cancel_edit_btn)
        
        edit_panel.addStretch()
        text_layout.addLayout(edit_panel)
        
        splitter.addWidget(text_widget)
        
        # Establecer tamaños iniciales
        splitter.setSizes([200, 800])  # 20% - 80%
        
        # Botones de exportación
        export_panel = QHBoxLayout()
        
        self.export_txt_btn = QPushButton("Exportar TXT")
        self.export_txt_btn.setEnabled(False)
        export_panel.addWidget(self.export_txt_btn)
        
        self.export_srt_btn = QPushButton("Exportar SRT")
        self.export_srt_btn.setEnabled(False)
        export_panel.addWidget(self.export_srt_btn)
        
        self.export_vtt_btn = QPushButton("Exportar VTT")
        self.export_vtt_btn.setEnabled(False)
        export_panel.addWidget(self.export_vtt_btn)
        
        self.export_all_btn = QPushButton("Exportar Todo")
        self.export_all_btn.setEnabled(False)
        export_panel.addWidget(self.export_all_btn)
        
        export_panel.addStretch()
        main_layout.addLayout(export_panel)
        
        # Barra de estado
        self.statusBar()
        
        self.setup_dictation_ui()
    
    def setup_menus(self):
        """Configura los menús de la aplicación"""
        # Menú Archivo
        file_menu = self.menuBar().addMenu("&Archivo")
        
        import_action = QAction("&Importar Audio/Video...", self)
        import_action.setShortcut("Ctrl+O")
        import_action.triggered.connect(self.import_files)
        file_menu.addAction(import_action)
        
        record_action = QAction("&Grabar Micrófono", self)
        record_action.setShortcut("Ctrl+R")
        record_action.triggered.connect(self.toggle_recording)
        file_menu.addAction(record_action)
        
        file_menu.addSeparator()
        
        export_menu = file_menu.addMenu("&Exportar")
        
        export_txt_action = QAction("Exportar &TXT", self)
        export_txt_action.triggered.connect(lambda: self.export_transcription("txt"))
        export_menu.addAction(export_txt_action)
        
        export_srt_action = QAction("Exportar &SRT", self)
        export_srt_action.triggered.connect(lambda: self.export_transcription("srt"))
        export_menu.addAction(export_srt_action)
        
        export_vtt_action = QAction("Exportar &VTT", self)
        export_vtt_action.triggered.connect(lambda: self.export_transcription("vtt"))
        export_menu.addAction(export_vtt_action)
        
        export_all_action = QAction("Exportar &Todo", self)
        export_all_action.triggered.connect(lambda: self.export_transcription("all"))
        export_menu.addAction(export_all_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("&Salir", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Menú Transcripción
        transcription_menu = self.menuBar().addMenu("&Transcripción")
        
        load_model_action = QAction("&Cargar Modelo", self)
        load_model_action.setShortcut("Ctrl+M")
        load_model_action.triggered.connect(self.load_model)
        transcription_menu.addAction(load_model_action)
        
        transcribe_action = QAction("&Transcribir", self)
        transcribe_action.setShortcut("Ctrl+T")
        transcribe_action.triggered.connect(self.transcribe)
        transcription_menu.addAction(transcribe_action)
        
        cancel_action = QAction("&Cancelar Transcripción", self)
        cancel_action.setShortcut("Esc")
        cancel_action.triggered.connect(self.cancel_transcription)
        transcription_menu.addAction(cancel_action)
        
        transcription_menu.addSeparator()
        
        advanced_action = QAction("Opciones &Avanzadas...", self)
        advanced_action.triggered.connect(self.show_advanced_options)
        transcription_menu.addAction(advanced_action)
        
        # Menú Herramientas
        tools_menu = self.menuBar().addMenu("&Herramientas")
        
        devices_action = QAction("&Dispositivos de Audio...", self)
        devices_action.triggered.connect(self.show_audio_devices)
        tools_menu.addAction(devices_action)
        
        tools_menu.addSeparator()
        
        config_action = QAction("&Configuración...", self)
        config_action.triggered.connect(self.show_config_dialog)
        tools_menu.addAction(config_action)
        
        # Añadir opción de dictado al menú Herramientas
        tools_menu.addSeparator()
        self.dictation_mode_action = QAction("Modo Dictado en Tiempo Real", self)
        self.dictation_mode_action.triggered.connect(self.toggle_dictation_mode)
        tools_menu.addAction(self.dictation_mode_action)
        
        # Menú Ayuda
        help_menu = self.menuBar().addMenu("A&yuda")
        
        about_action = QAction("&Acerca de...", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
    def setup_signals(self):
        """Configura las conexiones de señales"""
        # Botones principales
        self.load_model_btn.clicked.connect(self.load_model)
        self.import_btn.clicked.connect(self.import_files)
        self.record_btn.clicked.connect(self.toggle_recording)
        self.transcribe_btn.clicked.connect(self.transcribe)
        self.cancel_btn.clicked.connect(self.cancel_transcription)
        
        # Edición
        self.edit_btn.clicked.connect(self.enable_editing)
        self.save_edit_btn.clicked.connect(self.save_edits)
        self.cancel_edit_btn.clicked.connect(self.cancel_editing)
        
        # Exportación
        self.export_txt_btn.clicked.connect(lambda: self.export_transcription("txt"))
        self.export_srt_btn.clicked.connect(lambda: self.export_transcription("srt"))
        self.export_vtt_btn.clicked.connect(lambda: self.export_transcription("vtt"))
        self.export_all_btn.clicked.connect(lambda: self.export_transcription("all"))
        
        # Lista de archivos
        self.files_list.currentItemChanged.connect(self.file_selected)
        self.files_list.customContextMenuRequested.connect(self.show_file_context_menu)
        
        # Señales del transcriptor
        self.transcriber.signals.progress.connect(self.update_transcription_progress)
        self.transcriber.signals.finished.connect(self.transcription_finished)
        self.transcriber.signals.error.connect(self.transcription_error)
        self.transcriber.signals.cancelled.connect(self.transcription_cancelled)
        
        # Señales del grabador
        self.recorder.signals.recording_started.connect(self.recording_started)
        self.recorder.signals.recording_stopped.connect(self.recording_stopped)
        self.recorder.signals.recording_finished.connect(self.recording_finished)
        self.recorder.signals.recording_error.connect(self.recording_error)
        self.recorder.signals.recording_level.connect(self.update_recording_level)
        self.recorder.signals.recording_time.connect(self.update_recording_time)
        
        # Modelo y cierres
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)
    
    def setup_shortcuts(self):
        """Configura atajos de teclado adicionales"""
        # Ya se agregaron la mayoría a través de QAction en los menús
        
        # Eliminar archivo (Delete)
        delete_shortcut = QShortcut(QKeySequence("Delete"), self)
        delete_shortcut.activated.connect(self.remove_selected_file)
    
    def on_model_changed(self, index):
        """Gestiona cambios en la selección del modelo"""
        model_name = self.model_combo.currentText()
        
        # Advertir sobre modelos grandes
        if model_name in ["medium", "large"]:
            model_sizes = {
                "medium": "1.5GB",
                "large": "3GB"
            }
            
            QMessageBox.information(
                self,
                "Advertencia de Recursos",
                f"El modelo '{model_name}' requiere aproximadamente:\n\n"
                f"• {model_sizes.get(model_name, '1GB')} de RAM\n"
                f"• Mayor capacidad de procesamiento\n\n"
                f"El tiempo de carga y procesamiento será mayor."
            )
        
        # Actualizar configuración
        self.config.set("model_size", model_name)
    
    def import_files(self):
        """Importa archivos de audio/video"""
        file_filter = self.file_manager.get_supported_file_filter()
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Importar archivos de audio/video",
            self.config.get("last_import_dir", ""),
            file_filter
        )
        
        if not files:
            return
        
        # Guardar último directorio utilizado
        last_dir = os.path.dirname(files[0])
        self.config.set("last_import_dir", last_dir)
        
        # Importar cada archivo
        for file_path in files:
            self.import_file(file_path)
    
    def import_file(self, file_path, is_recording=False):
        """
        Importa un archivo específico
        
        Args:
            file_path (str): Ruta al archivo
            is_recording (bool): Si es un archivo de grabación
        """
        if not verify_ffmpeg_components():
            instructions = get_ffmpeg_install_instructions()
            QMessageBox.critical(
                self,
                "Error - FFMPEG/ffprobe no encontrados",
                "FFMPEG y/o ffprobe son necesarios para procesar archivos multimedia.\n\n" + instructions
            )
            return
        normalize = self.config.get("normalize_audio", False)
        self.import_btn.setEnabled(False)
        self.status_label.setText(f"Importando '{os.path.basename(file_path)}'...")
        self.progress_bar.setRange(0, 0)
        self.import_worker = ImportWorker(self.file_manager, file_path, normalize, is_recording)
        self.import_worker.finished.connect(self.on_import_finished)
        self.import_worker.start()

    def on_import_finished(self, file_info, file_path, is_recording, error):
        self.import_btn.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.status_label.setText("Listo")
        if error:
            logger.error(f"Error importando archivo: {error}")
            QMessageBox.critical(self, "Error", f"Error al importar archivo: {error}")
            return
        if not file_info:
            QMessageBox.warning(self, "Error al importar", f"No se pudo importar el archivo: {file_path}")
            return
        name = file_info['name']
        if is_recording:
            timestamp = file_info['created'].strftime("%Y%m%d_%H%M%S")
            name = f"Grabación_{timestamp}.wav"
            file_info['name'] = name
        base_name = name
        counter = 1
        while name in self.files:
            root, ext = os.path.splitext(base_name)
            name = f"{root}_{counter}{ext}"
            counter += 1
            file_info['name'] = name
        self.files[name] = file_info
        item = QListWidgetItem(name)
        self.files_list.addItem(item)
        self.files_list.setCurrentItem(item)
        if self.transcriber.model:
            self.transcribe_btn.setEnabled(True)
        logger.info(f"Archivo importado: {name}")
        self.statusBar().showMessage(f"Archivo importado: {name}", 3000)
    
    def load_model(self):
        """Carga el modelo seleccionado en un hilo y muestra el diálogo de descarga real"""
        model_name = self.model_combo.currentText()
        # Chequeo de memoria antes de modelos grandes
        if model_name in ["medium", "large"] and psutil is not None:
            ram_gb = psutil.virtual_memory().available / (1024**3)
            min_ram = 3 if model_name == "medium" else 6
            if ram_gb < min_ram:
                logger.warning(f"RAM disponible insuficiente para el modelo '{model_name}': {ram_gb:.1f} GB (recomendado: {min_ram} GB)")
                QMessageBox.warning(
                    self,
                    "Advertencia de memoria",
                    f"La memoria RAM disponible es baja ({ram_gb:.1f} GB).\n\nEl modelo '{model_name}' puede requerir al menos {min_ram} GB de RAM libre.\n\nLa aplicación podría fallar o volverse inestable."
                )
        self.status_label.setText(f"Cargando modelo '{model_name}'...")
        self.progress_bar.setValue(10)
        self.load_model_btn.setEnabled(False)
        self.transcribe_btn.setEnabled(False)
        QApplication.processEvents()

        # Crear diálogo de descarga
        dialog = ModelDownloadDialog(model_name, self)
        dialog.progress_bar.setValue(10)
        dialog.status_label.setText("Preparando descarga...")

        # Crear hilo de carga
        self.model_loader_thread = ModelLoaderThread(self.transcriber, model_name)
        self.model_loader_thread.progress.connect(lambda v, m: (dialog.progress_bar.setValue(v), dialog.status_label.setText(m)))
        
        def on_finish(success, model_name):
            dialog.accept()  # Cierra el diálogo
            self.load_model_btn.setEnabled(True)
            if success:
                self.status_label.setText(f"Modelo '{model_name}' cargado correctamente")
                if self.files_list.count() > 0:
                    self.transcribe_btn.setEnabled(True)
                self.progress_bar.setValue(100)
                self.statusBar().showMessage(f"Modelo {model_name} cargado", 3000)
            else:
                self.status_label.setText("Error al cargar modelo")
                self.progress_bar.setValue(0)
                QMessageBox.critical(
                    self,
                    "Error",
                    f"No se pudo cargar el modelo '{model_name}'.\n\nVerifica tu conexión a internet y el espacio disponible."
                )
            self.model_loader_thread = None

        self.model_loader_thread.finished.connect(on_finish)
        self.model_loader_thread.start()
        dialog.exec_()
    
    def toggle_recording(self):
        """Inicia o detiene la grabación de audio"""
        if not self.recorder.is_active():
            # Iniciar grabación
            success = self.recorder.start_recording()
            if not success:
                QMessageBox.critical(
                    self,
                    "Error de grabación",
                    "No se pudo iniciar la grabación.\n\n"
                    "Verifica tu micrófono y los permisos."
                )
        else:
            # Detener grabación
            self.recorder.stop_recording()
            # La señal de finalización gestionará el resultado
    
    def recording_started(self):
        """Gestiona el inicio de grabación"""
        self.record_btn.setText("Detener Grabación")
        self.status_label.setText("Grabando audio desde micrófono...")
        self.time_label.setText("00:00")
        self.progress_bar.setValue(0)
        
        # Deshabilitar botones incompatibles
        self.import_btn.setEnabled(False)
        self.transcribe_btn.setEnabled(False)
        
        self.statusBar().showMessage("Grabación en curso", 3000)
    
    def recording_stopped(self):
        """Gestiona la parada de grabación"""
        self.status_label.setText("Finalizando grabación...")
    
    def recording_finished(self, file_path):
        """Gestiona la finalización de grabación"""
        self.record_btn.setText("Grabar Micrófono")
        self.status_label.setText("Grabación completada")
        self.progress_bar.setValue(0)
        
        # Restaurar botones
        self.import_btn.setEnabled(True)
        
        # Importar el archivo grabado
        self.import_file(file_path, is_recording=True)
        
        self.statusBar().showMessage("Grabación finalizada", 3000)
    
    def recording_error(self, error_msg):
        """Gestiona errores de grabación"""
        self.record_btn.setText("Grabar Micrófono")
        self.status_label.setText("Error de grabación")
        self.progress_bar.setValue(0)
        
        # Restaurar botones
        self.import_btn.setEnabled(True)
        
        QMessageBox.critical(
            self,
            "Error de grabación",
            f"Error durante la grabación: {error_msg}"
        )
        
        self.statusBar().showMessage("Error de grabación", 3000)
    
    def update_recording_level(self, level):
        """Actualiza nivel de audio durante grabación"""
        if self.recorder.is_active():
            level_percent = min(int(level * 100), 100)
            self.progress_bar.setValue(level_percent)
    
    def update_recording_time(self, seconds):
        """Actualiza tiempo de grabación"""
        minutes = seconds // 60
        secs = seconds % 60
        self.time_label.setText(f"{minutes:02}:{secs:02}")
    
    def transcribe(self):
        """Inicia el proceso de transcripción"""
        # Chequeo de memoria antes de archivos largos
        current_item = self.files_list.currentItem()
        if current_item:
            file_name = current_item.text()
            if file_name in self.files:
                file_info = self.files[file_name]
                duration = file_info.get('duration', 0)
                if duration > 3600 and psutil is not None:  # Más de 1 hora
                    ram_gb = psutil.virtual_memory().available / (1024**3)
                    if ram_gb < 4:
                        logger.warning(f"RAM disponible baja para transcripción larga: {ram_gb:.1f} GB")
                        QMessageBox.warning(
                            self,
                            "Advertencia de memoria",
                            f"La memoria RAM disponible es baja ({ram_gb:.1f} GB).\n\nTranscribir archivos muy largos puede requerir al menos 4 GB de RAM libre.\n\nLa aplicación podría fallar o volverse inestable."
                        )
        if not self.transcriber.model:
            # Intentar cargar modelo automáticamente
            self.load_model()
            if not self.transcriber.model:
                return
        
        current_item = self.files_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self,
                "Selección requerida",
                "Selecciona un archivo para transcribir"
            )
            return
        
        file_name = current_item.text()
        if file_name not in self.files:
            QMessageBox.warning(
                self,
                "Archivo no encontrado",
                "El archivo seleccionado ya no existe"
            )
            return
        
        file_info = self.files[file_name]
        self.current_file = file_name
        
        # Obtener idioma seleccionado
        language = self.language_combo.currentData()
        translate_to = self.translate_combo.currentData()
        
        # Actualizar estado
        self.status_label.setText(f"Transcribiendo '{file_name}'...")
        self.progress_bar.setValue(0)
        
        # Deshabilitar controles durante transcripción
        self.transcribe_btn.setEnabled(False)
        self.import_btn.setEnabled(False)
        self.record_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        
        # Limpiar área de texto
        self.text_edit.clear()
        self.info_label.setText("Procesando...")
        
        # Iniciar transcripción en hilo secundario
        self.transcription_thread = TranscriptionThread(
            self.transcriber,
            file_info,
            language,
            translate_to
        )
        self.transcription_thread.start()
        
        self.statusBar().showMessage(f"Transcribiendo {file_name}...")
    
    @pyqtSlot(int, str)
    def update_transcription_progress(self, value, message):
        """Actualiza progreso de transcripción"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
    
    @pyqtSlot(dict)
    def transcription_finished(self, result):
        """Gestiona finalización de transcripción"""
        if not self.current_file:
            return
        
        # Guardar resultado
        self.results[self.current_file] = result
        
        # Mostrar resultado
        transcription = result["result"]
        self.text_edit.setPlainText(transcription["text"])
        
        # Mostrar información
        file_info = self.files[self.current_file]
        language = transcription.get("language", "desconocido")
        words = len(transcription["text"].split())
        duration = transcription.get("duration", 0)
        duration_str = f"{int(duration // 60)}:{int(duration % 60):02}"
        
        # Extraer palabras clave usando el idioma detectado
        lang_code = language if language and language != "desconocido" else "es"
        # Validar si el idioma está soportado por get_stopwords
        if not get_stopwords(lang_code):
            logger.warning(f"Idioma '{lang_code}' no soportado para palabras clave, usando 'es' como fallback.")
            lang_code = "es"
        keywords = extract_keywords(transcription["text"], language=lang_code)
        keywords_str = ", ".join(keywords)
        
        # Información de traducción si aplica
        translation_info = ""
        if result.get("translated", False):
            source_lang = result.get("language_source", "desconocido")
            target_lang = result.get("language_target", "desconocido")
            translation_info = f"<br><b>Traducción:</b> {source_lang} → {target_lang}"
        
        # Mostrar info
        self.info_label.setText(
            f"<b>Archivo:</b> {self.current_file}<br>"
            f"<b>Idioma detectado:</b> {language}{translation_info}<br>"
            f"<b>Palabras:</b> {words}<br>"
            f"<b>Duración:</b> {duration_str}<br>"
            f"<b>Palabras clave:</b> {keywords_str}<br>"
            f"<b>Tiempo de proceso:</b> {result['time']:.1f} segundos"
        )
        
        # Exportación automática si está configurada
        if self.config.get("auto_export", False):
            export_dir = self.config.get("export_directory")
            if export_dir and os.path.isdir(export_dir):
                # Generar nombre base para exportación
                base_name = os.path.splitext(self.current_file)[0]
                export_path = os.path.join(export_dir, base_name)
                
                # Exportar en formatos configurados
                formats = self.config.get("export_formats", ["txt", "srt", "vtt"])
                try:
                    self.file_manager.export_transcription(
                        transcription,
                        export_path,
                        formats
                    )
                    self.statusBar().showMessage(
                        f"Exportación automática completada en {export_dir}", 
                        5000
                    )
                except Exception as e:
                    logger.error(f"Error en exportación automática: {e}")
        
        # Actualizar controles
        self.progress_bar.setValue(100)
        self.status_label.setText("Transcripción completada")
        
        self.transcribe_btn.setEnabled(True)
        self.import_btn.setEnabled(True)
        self.record_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        # Habilitar botones de exportación y edición
        self.export_txt_btn.setEnabled(True)
        self.export_srt_btn.setEnabled(True)
        self.export_vtt_btn.setEnabled(True)
        self.export_all_btn.setEnabled(True)
        self.edit_btn.setEnabled(True)
        
        # Limpiar referencia al hilo
        self.transcription_thread = None
        
        self.statusBar().showMessage("Transcripción completada", 3000)
    
    @pyqtSlot(str)
    def transcription_error(self, error_msg):
        """Gestiona errores de transcripción"""
        self.progress_bar.setValue(0)
        self.status_label.setText("Error durante la transcripción")
        
        # Restaurar controles
        self.transcribe_btn.setEnabled(True)
        self.import_btn.setEnabled(True)
        self.record_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        # Mostrar error
        QMessageBox.critical(
            self,
            "Error de transcripción",
            f"Error durante la transcripción:\n\n{error_msg}"
        )
        
        # Limpiar referencia al hilo
        self.transcription_thread = None
        
        self.statusBar().showMessage("Error de transcripción", 3000)
    
    def transcription_cancelled(self):
        """Gestiona cancelación de transcripción"""
        self.progress_bar.setValue(0)
        self.status_label.setText("Transcripción cancelada")
        
        # Restaurar controles
        self.transcribe_btn.setEnabled(True)
        self.import_btn.setEnabled(True)
        self.record_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        # Limpiar referencia al hilo
        self.transcription_thread = None
        
        self.statusBar().showMessage("Transcripción cancelada", 3000)
    
    def cancel_transcription(self):
        """Cancela la transcripción en curso"""
        if not hasattr(self, 'transcriber') or self.transcriber is None or not self.cancel_btn.isEnabled():
            return
        
        reply = QMessageBox.question(
            self,
            "Confirmar cancelación",
            "¿Deseas cancelar la transcripción en curso?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.transcriber.cancel()
            self.status_label.setText("Cancelando transcripción...")
            self.cancel_btn.setEnabled(False)
    
    def file_selected(self, current, previous):
        """Gestiona cambio de selección de archivo"""
        if not current:
            # Limpiar interfaz
            self.text_edit.clear()
            self.info_label.setText("")
            
            # Deshabilitar botones
            self.export_txt_btn.setEnabled(False)
            self.export_srt_btn.setEnabled(False)
            self.export_vtt_btn.setEnabled(False)
            self.export_all_btn.setEnabled(False)
            self.edit_btn.setEnabled(False)
            
            return
        
        file_name = current.text()
        
        if file_name in self.results:
            # Hay transcripción - mostrarla
            result = self.results[file_name]
            transcription = result["result"]
            
            self.text_edit.setPlainText(transcription["text"])
            
            # Mostrar información
            file_info = self.files[file_name]
            language = transcription.get("language", "desconocido")
            words = len(transcription["text"].split())
            duration = transcription.get("duration", 0)
            duration_str = f"{int(duration // 60)}:{int(duration % 60):02}"
            
            # Información de traducción si aplica
            translation_info = ""
            if result.get("translated", False):
                source_lang = result.get("language_source", "desconocido")
                target_lang = result.get("language_target", "desconocido")
                translation_info = f"<br><b>Traducción:</b> {source_lang} → {target_lang}"
            
            # Mostrar info
            self.info_label.setText(
                f"<b>Archivo:</b> {file_name}<br>"
                f"<b>Idioma detectado:</b> {language}{translation_info}<br>"
                f"<b>Palabras:</b> {words}<br>"
                f"<b>Duración:</b> {duration_str}"
            )
            
            # Habilitar botones
            self.export_txt_btn.setEnabled(True)
            self.export_srt_btn.setEnabled(True)
            self.export_vtt_btn.setEnabled(True)
            self.export_all_btn.setEnabled(True)
            self.edit_btn.setEnabled(True)
            
        else:
            # No hay transcripción - mostrar información del archivo
            if file_name in self.files:
                file_info = self.files[file_name]
                
                # Formatear tamaño
                size_bytes = file_info.get('size', 0)
                size_str = ""
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size_bytes < 1024.0:
                        size_str = f"{size_bytes:.2f} {unit}"
                        break
                    size_bytes /= 1024.0
                
                # Formatear duración
                duration = file_info.get('duration', 0)
                if duration:
                    duration_str = f"{int(duration // 60)}:{int(duration % 60):02}"
                else:
                    duration_str = "Desconocida"
                
                # Mostrar información
                self.info_label.setText(
                    f"<b>Archivo:</b> {file_name}<br>"
                    f"<b>Ruta:</b> {file_info.get('original_path', '')}<br>"
                    f"<b>Tamaño:</b> {size_str}<br>"
                    f"<b>Duración:</b> {duration_str}<br>"
                    f"<b>Estado:</b> No transcrito"
                )
            
            # Limpiar área de texto
            self.text_edit.clear()
            
            # Deshabilitar botones de exportación y edición
            self.export_txt_btn.setEnabled(False)
            self.export_srt_btn.setEnabled(False)
            self.export_vtt_btn.setEnabled(False)
            self.export_all_btn.setEnabled(False)
            self.edit_btn.setEnabled(False)
        
        # Habilitar transcripción si hay modelo
        if self.transcriber.model and not self.transcription_thread:
            self.transcribe_btn.setEnabled(True)
        else:
            self.transcribe_btn.setEnabled(False)
    
    def show_file_context_menu(self, position):
        """Muestra menú contextual para lista de archivos"""
        if self.files_list.count() == 0:
            return
        
        current_item = self.files_list.currentItem()
        if not current_item:
            return
        
        file_name = current_item.text()
        
        menu = QMenu()
        
        # Acciones para todos los archivos
        transcribe_action = menu.addAction("Transcribir")
        transcribe_action.setEnabled(self.transcribe_btn.isEnabled())
        
        remove_action = menu.addAction("Eliminar de la lista")
        
        menu.addSeparator()
        
        # Acciones específicas para archivos con transcripción
        if file_name in self.results:
            export_menu = menu.addMenu("Exportar")
            export_menu.addAction("Exportar como TXT")
            export_menu.addAction("Exportar como SRT")
            export_menu.addAction("Exportar como VTT")
            export_menu.addAction("Exportar en todos los formatos")
            
            edit_action = menu.addAction("Editar transcripción")
        
        # Mostrar menú y procesar acción
        action = menu.exec_(self.files_list.mapToGlobal(position))
        
        if not action:
            return
        
        if action == transcribe_action:
            self.transcribe()
        
        elif action == remove_action:
            self.remove_selected_file()
        
        elif action.text() == "Exportar como TXT":
            self.export_transcription("txt")
        
        elif action.text() == "Exportar como SRT":
            self.export_transcription("srt")
        
        elif action.text() == "Exportar como VTT":
            self.export_transcription("vtt")
        
        elif action.text() == "Exportar en todos los formatos":
            self.export_transcription("all")
        
        elif action.text() == "Editar transcripción":
            self.enable_editing()
    
    def remove_selected_file(self):
        """Elimina el archivo seleccionado de la lista"""
        current_item = self.files_list.currentItem()
        if not current_item:
            return
        
        file_name = current_item.text()
        
        # Confirmar eliminación
        reply = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Deseas eliminar '{file_name}' de la lista?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Eliminar archivo de listas
        row = self.files_list.row(current_item)
        self.files_list.takeItem(row)
        
        # Eliminar resultados y referencias
        if file_name in self.results:
            del self.results[file_name]
        
        # Eliminar archivo temporal si es una grabación
        if file_name in self.files:
            file_info = self.files[file_name]
            if "processed_path" in file_info:
                file_path = file_info["processed_path"]
                if file_path.startswith(tempfile.gettempdir()) and os.path.exists(file_path):
                    try:
                        os.unlink(file_path)
                        logger.debug(f"Archivo temporal eliminado: {file_path}")
                    except Exception as e:
                        logger.warning(f"Error al eliminar archivo temporal: {e}")
            
            # Eliminar de la lista
            del self.files[file_name]
        
        # Deshabilitar transcripción si no hay más archivos
        if self.files_list.count() == 0:
            self.transcribe_btn.setEnabled(False)
        
        self.statusBar().showMessage(f"Archivo '{file_name}' eliminado", 3000)
    
    def export_transcription(self, format_type="txt"):
        """
        Exporta la transcripción actual
        
        Args:
            format_type (str): Formato a exportar (txt, srt, vtt, all)
        """
        current_item = self.files_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self,
                "Selección requerida",
                "Selecciona un archivo para exportar"
            )
            return
        
        file_name = current_item.text()
        
        if file_name not in self.results:
            QMessageBox.warning(
                self,
                "Sin transcripción",
                "El archivo seleccionado no tiene transcripción"
            )
            return
        
        # Obtener resultado
        result = self.results[file_name]
        transcription = result["result"]
        
        # Determinar formatos a exportar
        formats = []
        if format_type == "all":
            formats = ["txt", "srt", "vtt"]
        else:
            formats = [format_type]
        
        # Seleccionar ruta de exportación
        ext = "." + formats[0] if len(formats) == 1 else ""
        suggested_name = os.path.splitext(file_name)[0] + ext
        
        export_dir = self.config.get("export_directory", "")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar transcripción",
            os.path.join(export_dir, suggested_name),
            "Todos los archivos (*.*)"
        )
        
        if not file_path:
            return
        
        # Guardar directorio para próxima vez
        self.config.set("export_directory", os.path.dirname(file_path))
        
        # Eliminar extensión si se va a exportar en múltiples formatos
        if len(formats) > 1:
            file_path = os.path.splitext(file_path)[0]
        
        self.export_txt_btn.setEnabled(False)
        self.export_srt_btn.setEnabled(False)
        self.export_vtt_btn.setEnabled(False)
        self.export_all_btn.setEnabled(False)
        self.status_label.setText("Exportando transcripción...")
        self.progress_bar.setRange(0, 0)
        self.export_worker = ExportWorker(self.file_manager, transcription, file_path, formats)
        self.export_worker.finished.connect(self.on_export_finished)
        self.export_worker.start()

    def on_export_finished(self, exported, file_path, formats, error):
        self.export_txt_btn.setEnabled(True)
        self.export_srt_btn.setEnabled(True)
        self.export_vtt_btn.setEnabled(True)
        self.export_all_btn.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.status_label.setText("Listo")
        if error:
            logger.error(f"Error al exportar: {error}")
            QMessageBox.critical(self, "Error", f"Error al exportar transcripción: {error}")
            return
        if exported:
            formats_str = ", ".join(formats)
            exported_files = ", ".join(exported.values())
            QMessageBox.information(
                self,
                "Exportación completada",
                f"Transcripción exportada en formato(s): {formats_str}\n\nArchivos:\n{exported_files}"
            )
            self.statusBar().showMessage(f"Exportación completada: {formats_str}", 3000)
        else:
            QMessageBox.warning(self, "Error de exportación", "No se pudo exportar la transcripción")
    
    def enable_editing(self):
        """Habilita edición de transcripción"""
        if not self.edit_btn.isEnabled():
            return
        
        current_item = self.files_list.currentItem()
        if not current_item:
            return
        
        file_name = current_item.text()
        if file_name not in self.results:
            return
        
        # Guardar texto original
        self.original_text = self.text_edit.toPlainText()
        
        # Habilitar edición
        self.text_edit.setReadOnly(False)
        self.text_edit.setStyleSheet("background-color: #FFFFD0;")  # Fondo amarillo claro
        
        # Mostrar advertencia
        QMessageBox.warning(
            self,
            "Modo de edición",
            "Estás entrando en modo de edición.\n\n"
            "Ten en cuenta que editar el texto romperá la sincronización "
            "con los tiempos del audio en los formatos SRT/VTT.\n\n"
            "El texto completo seguirá exportándose, pero la información "
            "de tiempo puede no ser precisa."
        )
        
        # Actualizar botones
        self.edit_btn.setEnabled(False)
        self.save_edit_btn.setEnabled(True)
        self.cancel_edit_btn.setEnabled(True)
        
        # Deshabilitar botones de exportación SRT/VTT durante edición
        self.export_srt_btn.setEnabled(False)
        self.export_vtt_btn.setEnabled(False)
        
        self.statusBar().showMessage("Modo de edición activado", 3000)
    
    def save_edits(self):
        """Guarda los cambios de edición y actualiza los segmentos"""
        current_item = self.files_list.currentItem()
        if not current_item:
            return
        
        file_name = current_item.text()
        if file_name not in self.results:
            return
        
        # Obtener texto editado
        edited_text = self.text_edit.toPlainText()
        
        # Verificar si hay cambios
        if edited_text != self.original_text:
            # Confirmar aplicación de cambios
            reply = QMessageBox.question(
                self,
                "Confirmar cambios",
                "¿Aplicar cambios a la transcripción?\n\n"
                "Esto actualizará el texto pero mantendrá los tiempos originales.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Actualizar texto en el resultado principal
                self.results[file_name]["result"]["text"] = edited_text
                
                # Actualizar segmentos con el nuevo texto si es posible
                if "segments" in self.results[file_name]["result"]:
                    # Mostrar advertencia sobre limitaciones
                    QMessageBox.information(
                        self,
                        "Información sobre edición",
                        "Los cambios se han aplicado al texto completo.\n\n"
                        "Sin embargo, la información de tiempo de los subtítulos se mantiene como "
                        "en el original. Para una sincronización precisa, considera editar "
                        "los archivos SRT/VTT después de exportarlos."
                    )
                
                self.statusBar().showMessage("Cambios aplicados", 3000)
        
        # Restaurar estado de edición
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("")  # Restablecer estilo
        
        # Actualizar botones
        self.edit_btn.setEnabled(True)
        self.save_edit_btn.setEnabled(False)
        self.cancel_edit_btn.setEnabled(False)
        
        # Reactivar botones de exportación
        self.export_txt_btn.setEnabled(True)
        self.export_srt_btn.setEnabled(True)
        self.export_vtt_btn.setEnabled(True)
        self.export_all_btn.setEnabled(True)
    
    def cancel_editing(self):
        """Cancela la edición y restaura texto original"""
        # Restaurar texto original
        self.text_edit.setPlainText(self.original_text)
        
        # Restablecer estado de edición
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("")  # Restablecer estilo
        
        # Actualizar botones
        self.edit_btn.setEnabled(True)
        self.save_edit_btn.setEnabled(False)
        self.cancel_edit_btn.setEnabled(False)
        
        # Reactivar botones de exportación
        self.export_txt_btn.setEnabled(True)
        self.export_srt_btn.setEnabled(True)
        self.export_vtt_btn.setEnabled(True)
        self.export_all_btn.setEnabled(True)
        
        self.statusBar().showMessage("Edición cancelada", 3000)
    
    def show_config_dialog(self):
        """Muestra diálogo de configuración"""
        dialog = ConfigDialog(self.config, self)
        dialog.exec_()
    
    def show_audio_devices(self):
        """Muestra diálogo de selección de dispositivos de audio"""
        dialog = AudioDeviceDialog(self.config, self.recorder, self)
        dialog.exec_()
    
    def show_advanced_options(self):
        """Muestra diálogo de opciones avanzadas"""
        dialog = AdvancedOptionsDialog(self.config, self)
        dialog.exec_()
    
    def show_about_dialog(self):
        """Muestra diálogo 'Acerca de'"""
        dialog = AboutDialog(self)
        dialog.exec_()
    
    def closeEvent(self, event):
        """Gestiona cierre de la aplicación"""
        # Verificar si hay procesos activos
        if self.transcription_thread is not None and self.transcription_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirmar salida",
                "Hay una transcripción en curso. ¿Estás seguro de que quieres salir?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
            
            # Cancelar transcripción
            self.transcriber.cancel()
        
        # Verificar si hay grabación activa
        if self.recorder.is_active():
            reply = QMessageBox.question(
                self,
                "Confirmar salida",
                "Hay una grabación en curso. ¿Estás seguro de que quieres salir?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
            
            # Detener grabación
            self.recorder.stop_recording()
        
        # Limpiar archivos temporales
        self.file_manager.cleanup_temp_files()
        
        # Permitir cierre
        event.accept()

    def setup_dictation_ui(self):
        """Configura componentes de UI para el modo dictado"""
        self.dictation_widget = QWidget()
        dictation_layout = QVBoxLayout(self.dictation_widget)
        dictation_title = QLabel("Modo Dictado en Tiempo Real")
        font = dictation_title.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 2)
        dictation_title.setFont(font)
        dictation_title.setAlignment(Qt.AlignCenter)
        dictation_layout.addWidget(dictation_title)
        dictation_controls = QHBoxLayout()
        self.start_dictation_btn = QPushButton("Iniciar Dictado")
        self.start_dictation_btn.setIcon(QIcon.fromTheme("media-record"))
        self.start_dictation_btn.clicked.connect(self.toggle_dictation)
        dictation_controls.addWidget(self.start_dictation_btn)
        self.dictation_pause_btn = QPushButton("Pausar")
        self.dictation_pause_btn.setEnabled(False)
        self.dictation_pause_btn.clicked.connect(self.pause_dictation)
        dictation_controls.addWidget(self.dictation_pause_btn)
        self.dictation_clear_btn = QPushButton("Limpiar")
        self.dictation_clear_btn.clicked.connect(self.clear_dictation)
        dictation_controls.addWidget(self.dictation_clear_btn)
        dictation_layout.addLayout(dictation_controls)
        self.dictation_text = QTextEdit()
        self.dictation_text.setReadOnly(True)
        self.dictation_text.setPlaceholderText("El texto dictado aparecerá aquí en tiempo real...")
        dictation_layout.addWidget(self.dictation_text)
        export_controls = QHBoxLayout()
        self.dictation_export_txt_btn = QPushButton("Exportar como TXT")
        self.dictation_export_txt_btn.clicked.connect(lambda: self.export_dictation("txt"))
        export_controls.addWidget(self.dictation_export_txt_btn)
        self.dictation_to_editor_btn = QPushButton("Enviar a Editor")
        self.dictation_to_editor_btn.clicked.connect(self.dictation_to_editor)
        export_controls.addWidget(self.dictation_to_editor_btn)
        dictation_layout.addLayout(export_controls)
        self.dictation_status = QLabel("Listo para dictar")
        self.dictation_status.setStyleSheet("color: #666; font-style: italic;")
        dictation_layout.addWidget(self.dictation_status)
        self.dictation_widget.hide()

    def toggle_dictation_mode(self):
        """Alterna entre modo normal y modo dictado"""
        if not hasattr(self, 'dictation_widget'):
            self.setup_dictation_ui()
        if self.dictation_widget.isHidden():
            if not self.transcriber.model:
                reply = QMessageBox.question(
                    self,
                    "Cargar Modelo",
                    "Se necesita cargar un modelo para el dictado en tiempo real. ¿Cargar ahora?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    self.load_model()
                else:
                    return
            if not hasattr(self, 'realtime_transcriber'):
                self.realtime_transcriber = RealtimeTranscriber(self.transcriber, self.config)
                self.realtime_transcriber.signals.progress.connect(self.update_dictation_text)
                self.realtime_transcriber.signals.finished.connect(self.dictation_finished)
                self.realtime_transcriber.signals.error.connect(self.dictation_error)
                self.recorder.signals.recording_chunk.connect(self.realtime_transcriber.add_audio_chunk)
            central_layout = self.centralWidget().layout()
            if not hasattr(self, 'main_content_widget'):
                for i in range(central_layout.count()):
                    item = central_layout.itemAt(i)
                    if item and item.widget() and isinstance(item.widget(), QSplitter):
                        self.main_content_widget = item.widget()
                        break
            if hasattr(self, 'main_content_widget'):
                self.main_content_widget.hide()
            dictation_in_layout = False
            for i in range(central_layout.count()):
                if central_layout.itemAt(i).widget() == self.dictation_widget:
                    dictation_in_layout = True
                    break
            if not dictation_in_layout:
                central_layout.addWidget(self.dictation_widget, 1)
            self.dictation_widget.show()
            self.setWindowTitle("WhisperApp - Modo Dictado en Tiempo Real")
            if hasattr(self, 'dictation_mode_action'):
                self.dictation_mode_action.setText("Volver a Modo Normal")
        else:
            if hasattr(self, 'main_content_widget'):
                if hasattr(self, 'is_dictating') and self.is_dictating:
                    self.toggle_dictation()
                self.dictation_widget.hide()
                self.main_content_widget.show()
                self.setWindowTitle("WhisperApp - Transcripción de Audio/Video")
                if hasattr(self, 'dictation_mode_action'):
                    self.dictation_mode_action.setText("Modo Dictado en Tiempo Real")

    def toggle_dictation(self):
        """Inicia o detiene el dictado en tiempo real"""
        if not hasattr(self, 'is_dictating') or not self.is_dictating:
            if not self.transcriber.model:
                QMessageBox.warning(
                    self,
                    "Modelo no cargado",
                    "Se necesita cargar un modelo para el dictado en tiempo real."
                )
                return
            success = self.recorder.start_streaming_recording()
            if not success:
                QMessageBox.critical(
                    self,
                    "Error de Grabación",
                    "No se pudo iniciar la grabación para dictado.\n\nVerifica tu micrófono y los permisos."
                )
                return
            self.realtime_transcriber.start()
            self.is_dictating = True
            self.start_dictation_btn.setText("Detener Dictado")
            self.dictation_pause_btn.setEnabled(True)
            self.dictation_status.setText("Dictando... (habla con claridad)")
            self.dictation_status.setStyleSheet("color: #c00;")
            self.statusBar().showMessage("Dictado en tiempo real activo", 3000)
        else:
            self.realtime_transcriber.stop()
            self.recorder.stop_recording()
            self.is_dictating = False
            self.start_dictation_btn.setText("Iniciar Dictado")
            self.dictation_pause_btn.setEnabled(False)
            self.dictation_status.setText("Dictado detenido")
            self.dictation_status.setStyleSheet("color: #666; font-style: italic;")
            self.statusBar().showMessage("Dictado detenido", 3000)

    def pause_dictation(self):
        """Pausa o reanuda el dictado"""
        if self.dictation_pause_btn.text() == "Pausar":
            self.dictation_pause_btn.setText("Reanudar")
            self.dictation_status.setText("Dictado en pausa")
            self.recorder.stop_recording()
        else:
            self.dictation_pause_btn.setText("Pausar")
            self.dictation_status.setText("Dictado activo")
            self.recorder.start_streaming_recording()

    def update_dictation_text(self, text):
        """Actualiza el texto en el área de dictado"""
        self.dictation_text.setPlainText(text)
        cursor = self.dictation_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.dictation_text.setTextCursor(cursor)

    def dictation_finished(self, text):
        """Gestiona la finalización del dictado"""
        self.dictation_text.setPlainText(text)
        self.dictation_status.setText("Dictado completado")
        self.dictation_status.setStyleSheet("color: #060;")
        self.dictation_export_txt_btn.setEnabled(True)
        self.dictation_to_editor_btn.setEnabled(True)

    def dictation_error(self, error_msg):
        """Gestiona errores durante el dictado"""
        QMessageBox.critical(
            self,
            "Error de Dictado",
            f"Error durante el dictado en tiempo real:\n\n{error_msg}"
        )
        self.is_dictating = False
        self.start_dictation_btn.setText("Iniciar Dictado")
        self.dictation_pause_btn.setEnabled(False)
        self.dictation_status.setText("Error en dictado")
        self.dictation_status.setStyleSheet("color: #c00;")

    def clear_dictation(self):
        """Limpia el texto de dictado"""
        reply = QMessageBox.question(
            self,
            "Confirmar",
            "¿Estás seguro de que deseas limpiar todo el texto dictado?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.dictation_text.clear()
            if hasattr(self, 'realtime_transcriber'):
                self.realtime_transcriber.accumulated_text = ""

    def export_dictation(self, format_type="txt"):
        """Exporta el texto dictado a un archivo"""
        text = self.dictation_text.toPlainText()
        if not text:
            QMessageBox.warning(
                self,
                "Sin contenido",
                "No hay texto para exportar"
            )
            return
        export_dir = self.config.get("export_directory", "")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar texto dictado",
            os.path.join(export_dir, "dictado.txt"),
            "Archivos de texto (*.txt)"
        )
        if not file_path:
            return
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text)
            QMessageBox.information(
                self,
                "Exportación completada",
                f"Texto dictado guardado en:\n{file_path}"
            )
            self.statusBar().showMessage(f"Dictado exportado como {format_type.upper()}", 3000)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error al exportar",
                f"No se pudo guardar el archivo:\n\n{e}"
            )

    def dictation_to_editor(self):
        """Envía el texto dictado al editor de transcripción"""
        text = self.dictation_text.toPlainText()
        if not text:
            QMessageBox.warning(
                self,
                "Sin contenido",
                "No hay texto para enviar al editor"
            )
            return
        if self.text_edit.toPlainText():
            reply = QMessageBox.question(
                self,
                "Confirmar acción",
                "¿Deseas reemplazar el texto actual en el editor de transcripción?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        self.toggle_dictation_mode()
        self.text_edit.setPlainText(text)
        self.enable_editing()
        self.statusBar().showMessage("Texto dictado enviado al editor", 3000)