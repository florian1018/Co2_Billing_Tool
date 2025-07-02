# config.py : Modèles Pydantic pour validation et configuration application
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Annotated, Union, Optional
from datetime import date, datetime
import os
import json
from pathlib import Path
from co2tool.utils import logger

# Modèles de données pour validation
class CO2ConfigEntry(BaseModel):
    numero_article: Union[str, int] = Field(..., description="Numéro d'article")
    facteur_emission_co2: float = Field(..., ge=0, description="Facteur d'émission CO2 (>=0)")

class CO2ConfigFile(BaseModel):
    entries: list[CO2ConfigEntry]

class BillingLine(BaseModel):
    numero_article: Union[str, int] = Field(..., description="Numéro d'article")
    quantite: float = Field(..., ge=0, description="Quantité (>=0)")
    prix: float = Field(..., ge=0, description="Prix (>=0)")
    # D'autres colonnes métier peuvent être ajoutées dynamiquement
    
    model_config = {
        "extra": "allow"  # Autorise d'autres champs métier, mais valide les principaux
    }

# Type personnalisé pour la validation du format de date ISO
ISODate = Annotated[str, Field(pattern=r'^\d{4}-\d{2}-\d{2}$')]

# Configuration de l'application
class AppConfig(BaseModel):
    """Configuration globale de l'application, avec paramètres et options."""
    # Paramètres de filtrage par date
    filter_enabled: bool = Field(True, description="Activer le filtrage par date")
    
    # Date de début et de fin pour le filtrage (format ISO)
    filter_start_date: ISODate = Field(
        date(datetime.now().year, 1, 1).isoformat(), 
        description="Date de début pour le filtrage (format ISO YYYY-MM-DD)"
    )
    filter_end_date: ISODate = Field(
        date(datetime.now().year, 12, 31).isoformat(), 
        description="Date de fin pour le filtrage (format ISO YYYY-MM-DD)"
    )
    
    # Maintenir la compatibilité avec le code existant qui utilise filter_year
    filter_year: int = Field(datetime.now().year, description="Année pour filtrer les factures (déprécié)")
    
    # Paramètres d'affichage et de logs
    show_detailed_logs: bool = Field(False, description="Afficher les logs détaillés de diagnostic")
    default_export_format: str = Field("csv", description="Format d'export par défaut (csv ou xlsx)")
    
    # Métadonnées
    last_updated: str = Field(datetime.now().isoformat(), description="Date de dernière mise à jour")
    
    @model_validator(mode='after')
    def validate_date_range(self) -> 'AppConfig':
        """Vérifie que la date de fin est après la date de début"""
        try:
            start = date.fromisoformat(self.filter_start_date)
            end = date.fromisoformat(self.filter_end_date)
            
            if end < start:
                raise ValueError("La date de fin doit être après la date de début")
                
            # Mise à jour automatique de filter_year pour compatibilité
            self.filter_year = start.year
                
        except ValueError as e:
            if str(e) == "La date de fin doit être après la date de début":
                raise e
            raise ValueError("Format de date incorrect. Utiliser YYYY-MM-DD")
            
        return self
    
    model_config = {
        "extra": "ignore"  # Ignorer les champs supplémentaires lors de la désérialisation
    }

# Chemins des fichiers de configuration
CONFIG_DIR = Path(os.path.expanduser("~")) / ".co2tool"
CONFIG_FILE = CONFIG_DIR / "app_config.json"

# Instance par défaut
DEFAULT_CONFIG = AppConfig()

def load_app_config() -> AppConfig:
    """Charge la configuration depuis le fichier. Crée la configuration par défaut si nécessaire."""
    try:
        if not CONFIG_DIR.exists():
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            logger.info(f"Répertoire de configuration créé: {CONFIG_DIR}")
            
        if not CONFIG_FILE.exists():
            save_app_config(DEFAULT_CONFIG)
            logger.info(f"Fichier de configuration par défaut créé: {CONFIG_FILE}")
            return DEFAULT_CONFIG
            
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config_data = json.load(f)
            config = AppConfig(**config_data)
            logger.debug(f"Configuration chargée: {config}")
            return config
            
    except Exception as e:
        logger.exception(f"Erreur lors du chargement de la configuration")
        return DEFAULT_CONFIG

def save_app_config(config: AppConfig) -> bool:
    """Sauvegarde la configuration dans le fichier."""
    try:
        if not CONFIG_DIR.exists():
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            logger.info(f"Répertoire de configuration créé: {CONFIG_DIR}")
            
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config.model_dump(), f, indent=4, ensure_ascii=False)
            
        # Mettre à jour la configuration du logger
        logger.configure_logging(config.show_detailed_logs)
        logger.debug(f"Configuration sauvegardée: {config}")
        return True
    except Exception as e:
        logger.exception(f"Erreur lors de la sauvegarde de la configuration")
        return False

# Instance globale accessible
app_config = load_app_config()

# Initialiser le logger avec la configuration actuelle
logger.configure_logging(app_config.show_detailed_logs)
