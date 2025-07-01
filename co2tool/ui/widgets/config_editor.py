# config_editor.py : Éditeur configuration CO2
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog
from PySide6.QtCore import Signal
from pathlib import Path

class ConfigEditorWidget(QWidget):
    config_loaded = Signal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Aucun fichier de configuration CO2 chargé.")
        self.button = QPushButton("Charger configuration CO2")
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.button)
        self.button.clicked.connect(self.open_file_dialog)
        self.config_path = None

    def open_file_dialog(self):
        file, _ = QFileDialog.getOpenFileName(self, "Sélectionner le fichier de configuration CO2", "", "CSV Files (*.csv)")
        if file:
            self.config_path = Path(file)
            self.label.setText(f"Config chargée : {file}")
            self.config_loaded.emit(self.config_path)
