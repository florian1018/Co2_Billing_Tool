# data_viewer.py : Prévisualisation tableaux
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel
import pandas as pd

class DataViewerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Aucune donnée à afficher.")
        self.table = QTableWidget()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.table)
        self.table.hide()

    def set_dataframe(self, df: pd.DataFrame):
        if df is None or df.empty:
            self.label.setText("Aucune donnée à afficher.")
            self.table.hide()
            return
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels(df.columns.astype(str).tolist())
        for i, row in enumerate(df.itertuples(index=False)):
            for j, value in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(str(value)))
        self.label.setText("")
        self.table.show()
