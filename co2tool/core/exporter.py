# exporter.py : Export CSV/Excel
import pandas as pd
from pathlib import Path
from rich.console import Console

console = Console()

def export_to_csv(df: pd.DataFrame, output_path: Path) -> None:
    """Exporte le DataFrame au format CSV (UTF-8, séparateur point-virgule)."""
    try:
        df.to_csv(output_path, index=False, encoding="utf-8", sep=';')
        console.log(f"[green]Export CSV réussi : {output_path}")
    except Exception as e:
        console.log(f"[red]Erreur export CSV : {e}")
        raise

def export_to_excel(df: pd.DataFrame, output_path: Path) -> None:
    """Exporte le DataFrame au format Excel (XLSX)."""
    try:
        df.to_excel(output_path, index=False, engine="openpyxl")
        console.log(f"[green]Export Excel réussi : {output_path}")
    except Exception as e:
        console.log(f"[red]Erreur export Excel : {e}")
        raise
