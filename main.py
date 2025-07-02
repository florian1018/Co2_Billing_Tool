# Point d'entrée de l'application CO2 Billing Tool
from co2tool.core.config import app_config
from co2tool.utils import logger

if __name__ == "__main__":
    # Initialiser le logger avec la configuration actuelle
    logger.configure_logging(app_config.show_detailed_logs)
    logger.info("Démarrage de l'application CO2 Billing Tool")
    
    # Lancer l'interface graphique
    from co2tool.ui.main_window import launch_app
    launch_app()
