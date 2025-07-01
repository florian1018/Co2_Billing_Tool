# logger.py : Configuration logging avec rich
from rich.console import Console
from rich.logging import RichHandler
import logging

console = Console()

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console)]
)
logger = logging.getLogger("co2tool")
