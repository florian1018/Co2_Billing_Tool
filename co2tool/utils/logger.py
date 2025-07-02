# logger.py : Configuration logging avec rich
from rich.console import Console
from rich.logging import RichHandler
import logging
import sys
from functools import wraps
import inspect
from typing import Callable, Any, Optional

# Console rich pour affichage stylisé
console = Console()

# Configuration de base du logging
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True, tracebacks_extra_lines=2)]
)

# Logger principal de l'application
logger = logging.getLogger("co2tool")

# Variable globale qui sera mise à jour par app_config
show_detailed_logs = False

def configure_logging(detailed_logs: bool = False):
    """Configure le niveau de logging en fonction de app_config.show_detailed_logs"""
    global show_detailed_logs
    show_detailed_logs = detailed_logs
    
    if detailed_logs:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
        
def debug(message: str, *args, **kwargs):
    """Log un message de debug uniquement si show_detailed_logs est activé"""
    if show_detailed_logs:
        logger.debug(message, *args, **kwargs)

def info(message: str, *args, **kwargs):
    """Log un message d'information"""
    logger.info(message, *args, **kwargs)

def warning(message: str, *args, **kwargs):
    """Log un message d'avertissement"""
    logger.warning(message, *args, **kwargs)

def error(message: str, *args, **kwargs):
    """Log un message d'erreur"""
    logger.error(message, *args, **kwargs)

def exception(message: str, *args, **kwargs):
    """Log une exception avec traceback"""
    logger.exception(message, *args, **kwargs)

def log_function_call(func: Callable) -> Callable:
    """Décorateur pour logger l'entrée et la sortie des fonctions importantes en mode debug"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not show_detailed_logs:
            return func(*args, **kwargs)
            
        # Nom de la fonction et module
        fn_name = func.__name__
        module = inspect.getmodule(func).__name__
        
        # Extraction des noms d'arguments (pour une meilleure lisibilité)
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())
        
        # Format des arguments positionnels
        if len(args) > 0:
            if hasattr(args[0], '__class__') and args[0].__class__.__name__ in ['MainWindow', 'FileManagerWidget', 'ConfigEditorWidget', 'DataViewerWidget']:
                # Si c'est une méthode de classe, ne pas afficher self
                debug(f"→ {module}.{fn_name}({', '.join([f'{param_names[i+1]}={args[i+1]}' for i in range(len(args)-1)])})")
            else:
                debug(f"→ {module}.{fn_name}({', '.join([f'{param_names[i]}={args[i]}' for i in range(len(args))])})")
        else:
            debug(f"→ {module}.{fn_name}()")
        
        # Exécution de la fonction
        result = func(*args, **kwargs)
        
        # Log du résultat
        if result is not None:
            debug(f"← {module}.{fn_name} → {type(result).__name__}: {result}")
        else:
            debug(f"← {module}.{fn_name} → None")
            
        return result
        
    return wrapper
