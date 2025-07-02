# main_window.py : Fenêtre principale de l'application
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QFrame, QPushButton, QFileDialog, QMessageBox, QDateEdit,
                               QCheckBox, QGroupBox, QFormLayout, QGridLayout)
from PySide6.QtCore import QDate, Qt
from co2tool.ui.widgets.file_manager import FileManagerWidget
from co2tool.ui.widgets.config_editor import ConfigEditorWidget
from co2tool.ui.widgets.data_viewer import DataViewerWidget
from co2tool.core.loader import load_billing_csv_files, load_co2_config_csv
from co2tool.core.processor import process_billing_with_co2
from co2tool.core.config import app_config, AppConfig, save_app_config
from co2tool.utils.data_utils import filter_data_by_date_range, load_csv_with_encoding
from co2tool.utils import logger
from co2tool.utils.logger import log_function_call
import pandas as pd
import sys
import datetime
import os

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        # Titre avec plage de dates configurée
        start_date_display = datetime.date.fromisoformat(app_config.filter_start_date).strftime("%d/%m/%Y")
        end_date_display = datetime.date.fromisoformat(app_config.filter_end_date).strftime("%d/%m/%Y")
        self.setWindowTitle(f"CO2 Billing Tool - {start_date_display} à {end_date_display}")
        self.resize(1200, 700)
        main_layout = QHBoxLayout(self)

        # Zone 1 : Gestion fichiers CSV
        self.file_manager = FileManagerWidget()
        file_zone = QFrame()
        file_zone.setFrameShape(QFrame.StyledPanel)
        file_zone.setLayout(QVBoxLayout())
        file_zone.layout().addWidget(QLabel("1. Fichiers de facturation"))
        file_zone.layout().addWidget(self.file_manager)
        
        # Ajouter les contrôles de filtrage par date
        date_group = QGroupBox("Filtrage par date")
        date_group.setLayout(QFormLayout())
        
        # Case à cocher pour activer/désactiver le filtrage
        self.filter_checkbox = QCheckBox("Filtrer par plage de dates")
        self.filter_checkbox.setChecked(app_config.filter_enabled)
        date_group.layout().addRow(self.filter_checkbox)
        
        # Sélecteur de date de début
        self.start_date_edit = QDateEdit(calendarPopup=True)
        self.start_date_edit.setDisplayFormat("dd/MM/yyyy")
        start_date = QDate.fromString(app_config.filter_start_date, Qt.DateFormat.ISODate)
        self.start_date_edit.setDate(start_date)
        date_group.layout().addRow("Date de début:", self.start_date_edit)
        
        # Sélecteur de date de fin
        self.end_date_edit = QDateEdit(calendarPopup=True)
        self.end_date_edit.setDisplayFormat("dd/MM/yyyy")
        end_date = QDate.fromString(app_config.filter_end_date, Qt.DateFormat.ISODate)
        self.end_date_edit.setDate(end_date)
        date_group.layout().addRow("Date de fin:", self.end_date_edit)
        
        # Bouton pour appliquer les changements de date
        self.apply_date_button = QPushButton("Appliquer")
        date_group.layout().addRow(self.apply_date_button)
        
        # Ajouter le groupe de filtrage à la zone de fichiers
        file_zone.layout().addWidget(date_group)
        
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
        self.non_period_label = QLabel(self.get_non_period_label())
        self.non_period_zone.layout().addWidget(self.non_period_label)
        
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

        # Zone des boutons de traitement
        processing_buttons = QHBoxLayout()
        processing_label = QLabel("Traitement CO2:")
        processing_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        processing_buttons.addWidget(processing_label)
        
        # Bouton 1: Appliquer facteurs CO2 et conserver toutes les lignes
        self.process_keep_all_button = QPushButton("Appliquer facteurs CO2")
        self.process_keep_all_button.setToolTip("Applique les facteurs d'émission CO2 aux articles présents dans la configuration\nLes articles absents sont conservés avec facteur 0")
        self.process_keep_all_button.setEnabled(False)
        processing_buttons.addWidget(self.process_keep_all_button)
        
        # Bouton 2: Appliquer facteurs CO2 et filtrer les lignes sans correspondance
        self.process_filter_button = QPushButton("Appliquer et filtrer")
        self.process_filter_button.setToolTip("Applique les facteurs d'émission CO2 et supprime les articles absents de la configuration")
        self.process_filter_button.setEnabled(False)
        processing_buttons.addWidget(self.process_filter_button)
        
        preview_zone.layout().addLayout(processing_buttons)

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
        self.process_keep_all_button.clicked.connect(lambda: self.on_process_clicked(filter_missing=False))
        self.process_filter_button.clicked.connect(lambda: self.on_process_clicked(filter_missing=True))
        self.export_button.clicked.connect(self.on_export_clicked)
        self.view_non_period_button.clicked.connect(self.on_view_non_period_clicked)
        self.export_non_period_button.clicked.connect(self.on_export_non_period_clicked)
        
        # Connexions pour les contrôles de filtrage par date
        self.apply_date_button.clicked.connect(self.on_apply_date_filter)
        self.filter_checkbox.stateChanged.connect(self.on_filter_checkbox_changed)

    def get_non_period_label(self):
        """Génère le libellé pour la section des factures hors période"""
        if app_config.filter_enabled:
            start_date = datetime.date.fromisoformat(app_config.filter_start_date).strftime("%d/%m/%Y")
            end_date = datetime.date.fromisoformat(app_config.filter_end_date).strftime("%d/%m/%Y")
            return f"2b. Factures hors période ({start_date} - {end_date})"
        else:
            return "2b. Factures hors période"
    
    @log_function_call
    def on_filter_checkbox_changed(self, state):
        """Met à jour l'interface en fonction de l'état de la case à cocher de filtrage"""
        is_enabled = state == Qt.CheckState.Checked.value
        self.start_date_edit.setEnabled(is_enabled)
        self.end_date_edit.setEnabled(is_enabled)
        
    @log_function_call
    def on_apply_date_filter(self):
        """Applique les changements de configuration de filtrage par date"""
        # Mettre à jour la configuration
        app_config.filter_enabled = self.filter_checkbox.isChecked()
        app_config.filter_start_date = self.start_date_edit.date().toString(Qt.DateFormat.ISODate)
        app_config.filter_end_date = self.end_date_edit.date().toString(Qt.DateFormat.ISODate)
        
        # Mettre à jour l'interface
        self.setWindowTitle(f"CO2 Billing Tool - {app_config.filter_start_date} à {app_config.filter_end_date}")
        self.non_period_label.setText(self.get_non_period_label())
        
        # Sauvegarder la configuration
        save_app_config(app_config)
        logger.info(f"Configuration de filtrage mise à jour: {app_config.filter_start_date} à {app_config.filter_end_date}")
        
        # Si des fichiers sont déjà chargés, les refiltrer
        if hasattr(self, 'df_billing_raw') and self.df_billing_raw is not None:
            self.apply_date_filtering(self.df_billing_raw)
            self.data_viewer.set_dataframe(self.df_billing)
            QMessageBox.information(self, "Filtre appliqué", "La plage de dates a été mise à jour et appliquée aux données.")
    
    @log_function_call
    def apply_date_filtering(self, df):
        """Applique le filtrage par date sur le DataFrame"""
        if app_config.filter_enabled and "DATE_INVOICE" in df.columns:
            # Utiliser notre fonction utilitaire de filtrage par plage de dates
            self.df_billing, self.df_non_period = filter_data_by_date_range(
                df, 
                app_config.filter_start_date,
                app_config.filter_end_date,
                date_col="DATE_INVOICE"
            )
            
            # Stats pour l'affichage
            nb_in_period = len(self.df_billing)
            nb_out_period = len(self.df_non_period)
            
            logger.debug(f"Après filtrage: {nb_in_period} lignes dans la période, {nb_out_period} lignes hors période")
            
            # Mise à jour de l'info sur les factures hors période
            if nb_out_period > 0:
                self.non_period_info.setText(
                    f"{nb_out_period} factures hors période détectées dans {len(set(self.df_non_period['SOURCE_FILE']))} fichiers"
                )
                self.view_non_period_button.setEnabled(True)
                self.export_non_period_button.setEnabled(True)
            else:
                self.non_period_info.setText("Aucune facture hors période détectée")
                self.view_non_period_button.setEnabled(False)
                self.export_non_period_button.setEnabled(False)
        else:
            # Pas de filtrage par date ou colonne de date absente
            self.df_billing = df
            self.df_non_period = None
    
    @log_function_call
    def on_billing_files_loaded(self, file_paths):
        try:
            # Utiliser notre fonction centralisée de chargement CSV
            try:
                df_all, rapport = load_billing_csv_files(file_paths)
                logger.debug(f"Rapport de chargement: {rapport['nb_fichiers_inclus']} fichiers inclus, {rapport['nb_fichiers_exclus']} fichiers exclus")
                logger.info(f"Chargement terminé: {len(df_all)} lignes de factures depuis {len(file_paths)} fichiers")
            except Exception as e:
                raise ValueError(f"Erreur lors du chargement des fichiers CSV: {e}")
            
            # Garder une copie des données brutes non filtrées
            self.df_billing_raw = df_all
            
            # Appliquer le filtrage par date configuré
            self.apply_date_filtering(df_all)
            
            # Afficher les données filtrées
            self.data_viewer.set_dataframe(self.df_billing)
        except Exception as e:
            self.df_billing = None
            self.df_non_period = None
            self.data_viewer.set_dataframe(pd.DataFrame())
            logger.exception(f"Erreur chargement CSV")
            self.non_period_info.setText("Erreur lors du chargement des fichiers")
            self.view_non_period_button.setEnabled(False)
            self.export_non_period_button.setEnabled(False)
        
        self.update_process_button_state()

    @log_function_call
    def on_config_loaded(self, config_path):
        try:
            self.co2_config = load_co2_config_csv(config_path)  # DataFrame enrichi avec toutes les colonnes
            logger.debug(f"Configuration CO2 chargée: {len(self.co2_config)} lignes")
            logger.info(f"Configuration CO2 chargée depuis {config_path}")
                
        except Exception as e:
            self.co2_config = None
            logger.exception(f"Erreur chargement config CO2")
            
        self.update_process_button_state()

    def update_process_button_state(self):
        buttons_enabled = self.df_billing is not None and self.co2_config is not None
        self.process_keep_all_button.setEnabled(buttons_enabled)
        self.process_filter_button.setEnabled(buttons_enabled)

    @log_function_call
    def on_process_clicked(self, filter_missing=True):
        """Traite les données avec application des facteurs CO2, avec ou sans filtrage"""
        try:
            if self.df_billing is not None and self.co2_config is not None:
                # Mode de traitement selon le bouton utilisé
                self.df_result = process_billing_with_co2(
                    self.df_billing, 
                    self.co2_config, 
                    filter_missing_articles=filter_missing
                )
                
                # Mise à jour de l'interface
                self.data_viewer.set_dataframe(self.df_result)
                self.export_button.setEnabled(True)
                
                # Message selon le mode de traitement
                if filter_missing:
                    message = f"Traitement avec filtrage terminé: {len(self.df_result)} lignes conservées avec facteurs CO2"
                else:
                    nb_without_factors = (self.df_result["facteur_emission_co2"] == 0).sum()
                    message = f"Traitement sans filtrage terminé: {len(self.df_result)} lignes conservées dont {nb_without_factors} sans facteur CO2"
                
                logger.info(message)
                QMessageBox.information(self, "Traitement terminé", message)
                
        except Exception as e:
            self.df_result = None
            self.export_button.setEnabled(False)
            logger.exception(f"Erreur traitement CO2")
            QMessageBox.critical(self, "Erreur traitement", f"Erreur lors du traitement des données: {e}")

    def on_view_non_period_clicked(self):
        """Affiche les lignes hors période dans la prévisualisation"""
        if self.df_non_period is not None and not self.df_non_period.empty:
            self.data_viewer.set_dataframe(self.df_non_period)
            # Modifie temporairement le libellé du bouton d'affichage
            current_text = self.view_non_period_button.text()
            year = app_config.filter_year
            self.view_non_period_button.setText(f"Revenir aux factures {year}")
            
            # Switch de fonction : la prochaine fois, on revient aux factures de l'année configurée
            def restore_billing_view():
                self.data_viewer.set_dataframe(self.df_billing)
                self.view_non_period_button.setText(current_text)
                self.view_non_period_button.clicked.disconnect()
                self.view_non_period_button.clicked.connect(self.on_view_non_period_clicked)
            
            self.view_non_period_button.clicked.disconnect()
            self.view_non_period_button.clicked.connect(restore_billing_view)
    
    @log_function_call
    def on_export_non_period_clicked(self):
        """Exporte les lignes hors période vers un fichier CSV ou Excel"""
        if self.df_non_period is not None and not self.df_non_period.empty:
            from PySide6.QtWidgets import QFileDialog, QMessageBox
            import os
            
            # Utilisez le format par défaut configuré
            default_format = app_config.default_export_format.lower()
            filter_string = "CSV (*.csv);;Excel (*.xlsx)"
            selected_filter = "CSV (*.csv)" if default_format == "csv" else "Excel (*.xlsx)"
            
            file_path, selected_filter = QFileDialog.getSaveFileName(
                self, 
                f"Exporter les factures hors période {app_config.filter_year}", 
                os.path.expanduser("~"), 
                filter_string,
                selected_filter
            )
            
            if file_path:
                try:
                    from co2tool.core.exporter import export_to_csv, export_to_excel
                    if file_path.endswith(".csv"):
                        export_to_csv(self.df_non_period, file_path)
                    elif file_path.endswith(".xlsx"):
                        export_to_excel(self.df_non_period, file_path)
                    else:
                        QMessageBox.warning(self, "Erreur export", "Format non supporté. Choisissez .csv ou .xlsx.")
                        return
                    QMessageBox.information(self, "Export réussi", f"Les factures hors période ont été exportées vers {file_path}")
                except Exception as e:
                    QMessageBox.critical(self, "Erreur d'export", f"Impossible d'exporter les données: {str(e)}")
    
    @log_function_call
    def on_export_clicked(self):
        if self.df_result is None or len(self.df_result) == 0:
            logger.warning("Tentative d'export sans données")
            QMessageBox.warning(self, "Export impossible", "Aucune donnée traitée à exporter.")
            return
            
        # Utilisez le format par défaut configuré
        default_format = app_config.default_export_format.lower()
        filter_string = "CSV (*.csv);;Excel (*.xlsx)"
        selected_filter = "CSV (*.csv)" if default_format == "csv" else "Excel (*.xlsx)"
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Exporter le fichier", 
            os.path.expanduser("~"), 
            filter_string,
            selected_filter
        )
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
    from co2tool.utils import logger
    
    app = QApplication(sys.argv)
    
    # Charger la configuration de l'application avant de créer la fenêtre principale
    try:
        # Nous utilisons déjà le module config qui a chargé la configuration app_config
        logger.debug(f"Interface graphique CO2 Billing Tool initialisée avec filtrage du {app_config.filter_start_date} au {app_config.filter_end_date}")
    except Exception as e:
        logger.exception(f"Erreur lors du chargement de la configuration")
    
    window = MainWindow()
    window.show()
    logger.info("Interface utilisateur démarrée")
    sys.exit(app.exec())
