# main_window.py : Fenêtre principale de l'application
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QFrame, QPushButton, QFileDialog, QMessageBox)
from co2tool.ui.widgets.file_manager import FileManagerWidget
from co2tool.ui.widgets.config_editor import ConfigEditorWidget
from co2tool.ui.widgets.data_viewer import DataViewerWidget
from co2tool.core.loader import load_billing_csv_files, load_co2_config_csv
from co2tool.core.processor import process_billing_with_co2
import pandas as pd
import sys

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CO2 Billing Tool")
        self.resize(1200, 700)
        main_layout = QHBoxLayout(self)

        # Zone 1 : Gestion fichiers CSV
        self.file_manager = FileManagerWidget()
        file_zone = QFrame()
        file_zone.setFrameShape(QFrame.StyledPanel)
        file_zone.setLayout(QVBoxLayout())
        file_zone.layout().addWidget(QLabel("1. Fichiers de facturation"))
        file_zone.layout().addWidget(self.file_manager)
        main_layout.addWidget(file_zone, 2)

        # Zone 2 : Configuration CO2
        self.config_editor = ConfigEditorWidget()
        config_zone = QFrame()
        config_zone.setFrameShape(QFrame.StyledPanel)
        config_zone.setLayout(QVBoxLayout())
        config_zone.layout().addWidget(QLabel("2. Configuration CO2"))
        config_zone.layout().addWidget(self.config_editor)
        main_layout.addWidget(config_zone, 2)
        
        # Zone 2b : Analyses hors période
        self.non_period_zone = QFrame()
        self.non_period_zone.setFrameShape(QFrame.StyledPanel)
        self.non_period_zone.setLayout(QVBoxLayout())
        self.non_period_zone.layout().addWidget(QLabel("2b. Factures hors période (avant 2024)"))
        
        # Info sur factures hors période
        self.non_period_info = QLabel("Aucune facture hors période détectée")
        self.non_period_zone.layout().addWidget(self.non_period_info)
        
        # Boutons pour factures hors période
        non_period_buttons = QHBoxLayout()
        self.view_non_period_button = QPushButton("Afficher les factures hors période")
        self.view_non_period_button.setEnabled(False)
        self.export_non_period_button = QPushButton("Exporter les factures hors période")
        self.export_non_period_button.setEnabled(False)
        non_period_buttons.addWidget(self.view_non_period_button)
        non_period_buttons.addWidget(self.export_non_period_button)
        self.non_period_zone.layout().addLayout(non_period_buttons)
        
        main_layout.addWidget(self.non_period_zone, 1)

        # Zone 3 : Prévisualisation
        self.data_viewer = DataViewerWidget()
        preview_zone = QFrame()
        preview_zone.setFrameShape(QFrame.StyledPanel)
        preview_zone.setLayout(QVBoxLayout())
        preview_zone.layout().addWidget(QLabel("3. Prévisualisation & Export"))
        preview_zone.layout().addWidget(self.data_viewer)
        main_layout.addWidget(preview_zone, 3)

        # Bouton de traitement
        self.process_button = QPushButton("Filtrer/Traiter")
        self.process_button.setEnabled(False)
        preview_zone.layout().addWidget(self.process_button)

        # Bouton d'export
        self.export_button = QPushButton("Exporter")
        self.export_button.setEnabled(False)
        preview_zone.layout().addWidget(self.export_button)

        # États internes
        self.df_billing = None
        self.co2_config = None
        self.df_result = None
        self.df_non_period = None  # Factures hors période

        # Connexions
        self.file_manager.files_loaded.connect(self.on_billing_files_loaded)
        self.config_editor.config_loaded.connect(self.on_config_loaded)
        self.process_button.clicked.connect(self.on_process_clicked)
        self.export_button.clicked.connect(self.on_export_clicked)
        self.view_non_period_button.clicked.connect(self.on_view_non_period_clicked)
        self.export_non_period_button.clicked.connect(self.on_export_non_period_clicked)

    def on_billing_files_loaded(self, file_paths):
        try:
            # On ajoute le fichier source comme information pour chaque ligne
            all_dataframes = []
            for file_path in file_paths:
                try:
                    df = pd.read_csv(file_path, dtype=str, engine="pyarrow", sep=';', encoding='utf-8')
                    # Ajout du fichier source comme colonne
                    df["SOURCE_FILE"] = str(file_path)
                    all_dataframes.append(df)
                except UnicodeDecodeError:
                    print(f"Encodage utf-8 échoué pour {file_path}, tentative avec 'latin1'.")
                    df = pd.read_csv(file_path, dtype=str, engine="pyarrow", sep=';', encoding='latin1')
                    df["SOURCE_FILE"] = str(file_path)
                    all_dataframes.append(df)
            
            # Concaténation de tous les fichiers
            combined_df = pd.concat(all_dataframes, ignore_index=True)
            
            # Mapping des colonnes standard
            column_mapping = {
                "ID_MATERIAL": "numero_article",
                "QUANTITY": "quantite",
                "AMOUNT_NET": "prix"
            }
            combined_df = combined_df.rename(columns={col: column_mapping.get(col, col) for col in combined_df.columns if col in column_mapping})
            
            # Filtrage sur les factures de 2024 uniquement
            self.df_non_period = None  # Réinitialisation
            if "DATE_INVOICE" in combined_df.columns:
                print(f"Filtrage des factures sur l'année 2024... {len(combined_df)} lignes avant filtrage")
                # Conversion des dates avec gestion des erreurs
                temp_df = combined_df.copy()
                temp_df["DATE_TEMP"] = pd.to_datetime(temp_df["DATE_INVOICE"], errors="coerce", dayfirst=True)
                
                # Filtre sur l'année 2024
                mask_2024 = (temp_df["DATE_TEMP"] >= pd.Timestamp("2024-01-01")) & \
                            (temp_df["DATE_TEMP"] <= pd.Timestamp("2024-12-31"))
                
                # Séparation des données 2024 et hors période
                self.df_billing = combined_df[mask_2024].reset_index(drop=True)
                self.df_non_period = combined_df[~mask_2024].reset_index(drop=True)
                
                # Stats pour l'affichage
                nb_in_period = len(self.df_billing)
                nb_out_period = len(self.df_non_period)
                print(f"Après filtrage: {nb_in_period} lignes de 2024 conservées, {nb_out_period} lignes hors période")
                
                # Mise à jour de l'info sur les factures hors période
                if nb_out_period > 0:
                    self.non_period_info.setText(f"{nb_out_period} factures hors période détectées dans {len(set(self.df_non_period['SOURCE_FILE']))} fichiers")
                    self.view_non_period_button.setEnabled(True)
                    self.export_non_period_button.setEnabled(True)
                else:
                    self.non_period_info.setText("Aucune facture hors période détectée")
                    self.view_non_period_button.setEnabled(False)
                    self.export_non_period_button.setEnabled(False)
            else:
                self.df_billing = combined_df
            
            self.data_viewer.set_dataframe(self.df_billing)
        except Exception as e:
            self.df_billing = None
            self.df_non_period = None
            self.data_viewer.set_dataframe(pd.DataFrame())
            print(f"Erreur chargement CSV : {e}")
            self.non_period_info.setText("Erreur lors du chargement des fichiers")
            self.view_non_period_button.setEnabled(False)
            self.export_non_period_button.setEnabled(False)
        
        self.update_process_button_state()

    def on_config_loaded(self, config_path):
        try:
            self.co2_config = load_co2_config_csv(config_path)  # DataFrame enrichi avec toutes les colonnes
        except Exception as e:
            self.co2_config = None
            print(f"Erreur chargement config CO2 : {e}")
        self.update_process_button_state()

    def update_process_button_state(self):
        self.process_button.setEnabled(self.df_billing is not None and self.co2_config is not None)

    def on_process_clicked(self):
        if self.df_billing is not None and self.co2_config is not None:
            try:
                # self.co2_config est déjà un DataFrame enrichi avec toutes les colonnes de la config CO2
                self.df_result = process_billing_with_co2(self.df_billing, self.co2_config)
                self.data_viewer.set_dataframe(self.df_result)
                self.export_button.setEnabled(True)
            except Exception as e:
                print(f"Erreur traitement CO2 : {e}")
                self.export_button.setEnabled(False)

    def on_view_non_period_clicked(self):
        """Affiche les lignes hors période (avant 2024) dans la prévisualisation"""
        if self.df_non_period is not None and not self.df_non_period.empty:
            self.data_viewer.set_dataframe(self.df_non_period)
            # Modifie temporairement le libellé du bouton d'affichage
            current_text = self.view_non_period_button.text()
            self.view_non_period_button.setText("Revenir aux factures 2024")
            
            # Switch de fonction : la prochaine fois, on revient aux factures 2024
            def restore_billing_view():
                self.data_viewer.set_dataframe(self.df_billing)
                self.view_non_period_button.setText(current_text)
                self.view_non_period_button.clicked.disconnect()
                self.view_non_period_button.clicked.connect(self.on_view_non_period_clicked)
            
            self.view_non_period_button.clicked.disconnect()
            self.view_non_period_button.clicked.connect(restore_billing_view)
    
    def on_export_non_period_clicked(self):
        """Exporte les lignes hors période vers un fichier CSV"""
        if self.df_non_period is not None and not self.df_non_period.empty:
            from PySide6.QtWidgets import QFileDialog
            
            file_path, selected_filter = QFileDialog.getSaveFileName(
                self, 
                "Exporter les factures hors période", 
                "", 
                "CSV (*.csv);;Tous les fichiers (*.*)"
            )
            
            if file_path:
                try:
                    # Export au format CSV avec séparateur ;
                    self.df_non_period.to_csv(file_path, sep=';', index=False, encoding='utf-8')
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.information(self, "Export réussi", 
                                       f"Les factures hors période ont été exportées vers {file_path}")
                except Exception as e:
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.critical(self, "Erreur d'export", 
                                     f"Impossible d'exporter les données: {str(e)}")
    
    def on_export_clicked(self):
        if self.df_result is None or self.df_result.empty:
            print("Aucune donnée à exporter.")
            return
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        import os
        file_path, _ = QFileDialog.getSaveFileName(self, "Exporter le fichier", os.path.expanduser("~"), "CSV (*.csv);;Excel (*.xlsx)")
        if not file_path:
            return
        try:
            from co2tool.core.exporter import export_to_csv, export_to_excel
            if file_path.endswith(".csv"):
                export_to_csv(self.df_result, file_path)
            elif file_path.endswith(".xlsx"):
                export_to_excel(self.df_result, file_path)
            else:
                QMessageBox.warning(self, "Erreur export", "Format non supporté. Choisissez .csv ou .xlsx.")
                return
            QMessageBox.information(self, "Export réussi", f"Fichier exporté : {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur export", str(e))

def launch_app():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
