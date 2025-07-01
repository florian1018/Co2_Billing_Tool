# file_manager.py : Gestion fichiers CSV + drag&drop
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton, QFileDialog
from PySide6.QtCore import Signal, Qt
from pathlib import Path

class FileManagerWidget(QWidget):
    files_loaded = Signal(list)  # Liste de chemins de fichiers

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.selected_files = []
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Déposez vos fichiers CSV ici ou cliquez sur 'Ajouter'")
        self.list_widget = QListWidget()
        self.add_button = QPushButton("Ajouter des fichiers CSV")
        self.clear_button = QPushButton("Vider la liste")
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.list_widget)
        self.layout.addWidget(self.add_button)
        self.layout.addWidget(self.clear_button)
        self.add_button.clicked.connect(self.open_file_dialog)
        self.clear_button.clicked.connect(self.clear_files)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.toLocalFile().endswith('.csv')]
        self.add_files(files)

    def open_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Sélectionner des fichiers CSV", "", "CSV Files (*.csv)")
        self.add_files([Path(f) for f in files])

    def add_files(self, files):
        for f in files:
            if f not in self.selected_files and f.exists():
                self.selected_files.append(f)
                self.list_widget.addItem(str(f))
        if self.selected_files:
            self.files_loaded.emit(self.selected_files)

    def clear_files(self):
        self.selected_files = []
        self.list_widget.clear()
