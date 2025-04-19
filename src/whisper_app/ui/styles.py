"""
Módulo de estilos y temas para WhisperApp
Proporciona diferentes temas para la aplicación
"""

from PyQt5.QtGui import QPalette, QColor, QIcon
from PyQt5.QtCore import Qt


def apply_theme(app, theme="dark"):
    """
    Aplica un tema a toda la aplicación
    
    Args:
        app: Instancia de QApplication
        theme: Nombre del tema (system, light, dark, elegant_dark)
    """
    if theme == "system":
        # Usar tema del sistema
        app.setStyle("Fusion")
        app.setPalette(QPalette())
    elif theme == "light":
        _apply_light_theme(app)
    elif theme == "dark":
        _apply_dark_theme(app)
    elif theme == "elegant_dark":
        _apply_elegant_dark_theme(app)
    else:
        # Por defecto, tema elegante oscuro
        _apply_elegant_dark_theme(app)


def _apply_light_theme(app):
    """Aplica tema claro básico"""
    app.setStyle("Fusion")
    palette = QPalette()
    app.setPalette(palette)
    app.setStyleSheet("")


def _apply_dark_theme(app):
    """Aplica tema oscuro básico (Fusion)"""
    app.setStyle("Fusion")
    palette = QPalette()
    
    # Colores base oscuros
    dark_color = QColor(45, 45, 45)
    disabled_color = QColor(70, 70, 70)
    text_color = QColor(210, 210, 210)
    
    palette.setColor(QPalette.Window, dark_color)
    palette.setColor(QPalette.WindowText, text_color)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, dark_color)
    palette.setColor(QPalette.ToolTipBase, dark_color)
    palette.setColor(QPalette.ToolTipText, text_color)
    palette.setColor(QPalette.Text, text_color)
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(150, 150, 150))
    palette.setColor(QPalette.Button, dark_color)
    palette.setColor(QPalette.ButtonText, text_color)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(150, 150, 150))
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    palette.setColor(QPalette.Disabled, QPalette.Highlight, disabled_color)
    
    app.setPalette(palette)


def _apply_elegant_dark_theme(app):
    """Aplica tema oscuro elegante y moderno con acentos de color"""
    app.setStyle("Fusion")
    
    # Color principal de acento
    accent_color = QColor(61, 174, 233)  # Azul elegante
    accent_disabled = QColor(40, 110, 150)
    
    # Colores base para el tema oscuro
    window_color = QColor(30, 30, 30)  # Fondo muy oscuro
    widget_color = QColor(45, 45, 45)  # Widgets un poco más claros
    widget_alt_color = QColor(53, 53, 53)  # Alternativa para widgets
    text_color = QColor(240, 240, 240)  # Texto casi blanco
    disabled_text = QColor(150, 150, 150)  # Texto deshabilitado
    
    # Crear paleta
    palette = QPalette()
    palette.setColor(QPalette.Window, window_color)
    palette.setColor(QPalette.WindowText, text_color)
    palette.setColor(QPalette.Base, widget_color)
    palette.setColor(QPalette.AlternateBase, widget_alt_color)
    palette.setColor(QPalette.ToolTipBase, widget_color)
    palette.setColor(QPalette.ToolTipText, text_color)
    palette.setColor(QPalette.Text, text_color)
    palette.setColor(QPalette.Disabled, QPalette.Text, disabled_text)
    palette.setColor(QPalette.Button, widget_color)
    palette.setColor(QPalette.ButtonText, text_color)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, disabled_text)
    palette.setColor(QPalette.BrightText, Qt.white)
    palette.setColor(QPalette.Link, accent_color)
    palette.setColor(QPalette.Highlight, accent_color)
    palette.setColor(QPalette.HighlightedText, Qt.white)
    palette.setColor(QPalette.Disabled, QPalette.Highlight, accent_disabled)
    
    app.setPalette(palette)
    
    # Estilos adicionales con CSS para perfeccionar la apariencia
    app.setStyleSheet("""
        QMainWindow, QDialog {
            background-color: #1e1e1e;
        }
        
        QWidget {
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        
        QPushButton {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
            border-radius: 4px;
            padding: 6px 12px;
            min-width: 80px;
        }
        
        QPushButton:hover {
            background-color: #353535;
            border-color: #3DAEE9;
        }
        
        QPushButton:pressed {
            background-color: #383838;
        }
        
        QPushButton:disabled {
            background-color: #2d2d2d;
            color: #808080;
            border-color: #3d3d3d;
        }
        
        QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
            border-radius: 4px;
            padding: 3px;
            selection-background-color: #3DAEE9;
        }
        
        QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {
            border-color: #3DAEE9;
        }
        
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        
        QProgressBar {
            border: 1px solid #3d3d3d;
            border-radius: 3px;
            text-align: center;
            background-color: #2d2d2d;
        }
        
        QProgressBar::chunk {
            background-color: #3DAEE9;
            width: 10px;
        }
        
        QTabWidget::pane {
            border: 1px solid #3d3d3d;
        }
        
        QTabBar::tab {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
            border-bottom: none;
            min-width: 8ex;
            padding: 6px;
        }
        
        QTabBar::tab:selected {
            background-color: #3d3d3d;
            border-bottom: 1px solid #3DAEE9;
        }
        
        QTabBar::tab:!selected {
            margin-top: 2px;
        }
        
        QListWidget, QTreeWidget, QTableWidget {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
            alternate-background-color: #353535;
        }
        
        QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected {
            background-color: #3DAEE9;
            color: white;
        }
        
        QListWidget::item:hover, QTreeWidget::item:hover, QTableWidget::item:hover {
            background-color: #353535;
        }
        
        QGroupBox {
            border: 1px solid #3d3d3d;
            border-radius: 4px;
            margin-top: 16px;
            font-weight: bold;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 5px;
        }
        
        QSplitter::handle {
            background-color: #3d3d3d;
        }
        
        QScrollBar:vertical {
            border: none;
            background-color: #2d2d2d;
            width: 10px;
            margin: 0px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #3d3d3d;
            min-height: 20px;
            border-radius: 5px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #3DAEE9;
        }
        
        QScrollBar:horizontal {
            border: none;
            background-color: #2d2d2d;
            height: 10px;
            margin: 0px;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #3d3d3d;
            min-width: 20px;
            border-radius: 5px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #3DAEE9;
        }
        
        QMenuBar {
            background-color: #222222;
            color: #f0f0f0;
            border-bottom: 1px solid #3d3d3d;
        }
        
        QMenuBar::item {
            background: transparent;
        }
        
        QMenuBar::item:selected {
            background: #3d3d3d;
        }
        
        QMenu {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
        }
        
        QMenu::item {
            padding: 5px 20px 5px 20px;
        }
        
        QMenu::item:selected {
            background-color: #3DAEE9;
            color: white;
        }
        
        QMenu::separator {
            height: 1px;
            background: #3d3d3d;
            margin: 5px;
        }
        
        QStatusBar {
            background-color: #222222;
            color: #f0f0f0;
            border-top: 1px solid #3d3d3d;
        }
        
        AudioLevelMeter QProgressBar {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
        }
        
        AudioLevelMeter QProgressBar::chunk {
            background-color: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #0a8, stop:0.7 #0d0, stop:1 #f00
            );
        }
    """)


# Paleta de colores elegante para referencia
ELEGANT_DARK_PALETTE = {
    "background": "#1E1E1E",
    "widget_background": "#2D2D2D",
    "widget_alt_background": "#353535",
    "border": "#3D3D3D",
    "text": "#F0F0F0",
    "accent": "#3DAEE9",
    "accent_alt": "#2980B9",
    "success": "#27AE60",
    "warning": "#F39C12",
    "error": "#E74C3C",
    "disabled": "#808080",
}
