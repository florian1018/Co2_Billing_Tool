# data_utils.py : Utilitaires de traitement de données
import re
import pandas as pd
import datetime
from typing import Optional, Union, Tuple
from pathlib import Path

def parse_float(val) -> Optional[float]:
    """
    Convertit proprement une chaîne de caractères en float avec gestion des formats internationaux.
    Gère les espaces insécables, virgules, points, espaces standards, etc.
    
    Args:
        val: La valeur à convertir (string, int, float, etc.)
        
    Returns:
        float ou None si la conversion échoue
    """
    try:
        if pd.isna(val):
            return None
            
        s = str(val).strip().replace("\u202f", "").replace("\xa0", "")  # espaces insécables
        s = s.replace(" ", "")  # espaces
        s = s.replace(",", ".")  # décimale
        
        if s.count(".") > 1:
            # Format US : 1,470.000 -> 1470.000
            s = s.replace(".", "", s.count(".") - 1)
        s = s.replace(",", "")  # supprime toute virgule résiduelle
        
        return float(s)
    except Exception:
        return None

def load_csv_with_encoding(file_path: Union[str, Path], sep: str = ';', **kwargs) -> pd.DataFrame:
    """
    Charge un fichier CSV en essayant différents encodages (UTF-8, puis Latin1).
    
    Args:
        file_path: Chemin du fichier CSV
        sep: Séparateur de colonnes
        **kwargs: Arguments supplémentaires pour pd.read_csv
        
    Returns:
        DataFrame pandas
        
    Raises:
        Exception: Si le chargement échoue avec tous les encodages
    """
    encodings = ["utf-8", "latin1"]
    
    for encoding in encodings:
        try:
            return pd.read_csv(file_path, sep=sep, encoding=encoding, **kwargs)
        except UnicodeDecodeError:
            continue
    
    # Si on arrive ici, aucun encodage n'a fonctionné
    raise UnicodeDecodeError(f"Impossible de charger {file_path} avec les encodages disponibles: {encodings}")

def clean_numero_article_column(df: pd.DataFrame, col: str = "numero_article") -> pd.DataFrame:
    """
    Nettoie la colonne des numéros d'article en supprimant les zéros initiaux.
    Les numéros d'article ne commencent jamais par zéro (ex : "0000001234567" -> "1234567").
    Args:
        df: DataFrame à nettoyer
        col: Nom de la colonne à nettoyer
    Returns:
        DataFrame avec la colonne nettoyée
    """
    if col not in df.columns:
        return df
    result = df.copy()
    # On force le type str pour éviter les erreurs
    result[col] = result[col].astype(str).apply(lambda x: re.sub(r'^0+(\d+)$', r'\1', x) if x.isdigit() else x)
    return result

def clean_quantity_column(df: pd.DataFrame, col: str = "quantite") -> pd.DataFrame:
    """
    Nettoie une colonne de quantités en la convertissant en float lorsque possible.
    
    Args:
        df: DataFrame à nettoyer
        col: Nom de la colonne à nettoyer
        
    Returns:
        DataFrame avec la colonne nettoyée
    """
    if col not in df.columns:
        return df
        
    # Créer une copie pour éviter les avertissements de SettingWithCopyWarning
    result = df.copy()
    
    # Appliquer parse_float à chaque valeur
    result[col] = result[col].apply(parse_float)
    
    return result

def filter_data_by_year(df: pd.DataFrame, year: int = 2024, date_col: str = "DATE_INVOICE") -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Filtre un DataFrame pour extraire les données d'une année spécifique et retourne également les données hors période.
    Pour une filtration plus précise, utilisez plutôt filter_data_by_date_range.
    
    Args:
        df: DataFrame à filtrer
        year: Année à conserver
        date_col: Nom de la colonne de date
        
    Returns:
        Tuple (données de l'année, données hors période)
    """
    # Convertir l'année en plage de dates complète
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    # Utiliser la nouvelle fonction avec la plage de dates
    return filter_data_by_date_range(df, start_date, end_date, date_col)

def filter_data_by_date_range(df: pd.DataFrame, 
                              start_date: Union[str, datetime.date] = None, 
                              end_date: Union[str, datetime.date] = None, 
                              date_col: str = "DATE_INVOICE") -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Filtre un DataFrame pour extraire les données entre deux dates et retourne également les données hors période.
    
    Args:
        df: DataFrame à filtrer
        start_date: Date de début (format ISO YYYY-MM-DD ou objet datetime.date)
        end_date: Date de fin (format ISO YYYY-MM-DD ou objet datetime.date)
        date_col: Nom de la colonne de date
        
    Returns:
        Tuple (données dans la plage de dates, données hors plage)
    """
    if date_col not in df.columns:
        return df, pd.DataFrame()
    
    # Conversion des paramètres de date si nécessaire
    if start_date is None:
        # Par défaut, début de l'année en cours
        start_date = datetime.date(datetime.datetime.now().year, 1, 1)
    elif isinstance(start_date, str):
        start_date = pd.Timestamp(start_date)
    else:
        start_date = pd.Timestamp(start_date.isoformat())
        
    if end_date is None:
        # Par défaut, fin de l'année en cours
        end_date = datetime.date(datetime.datetime.now().year, 12, 31)
    elif isinstance(end_date, str):
        end_date = pd.Timestamp(end_date)
    else:
        end_date = pd.Timestamp(end_date.isoformat())
    
    # Conversion des dates avec gestion des erreurs
    temp_df = df.copy()
    temp_df["DATE_TEMP"] = pd.to_datetime(temp_df[date_col], errors="coerce", dayfirst=True)
    
    # Filtre sur la plage de dates spécifiée
    mask_period = (temp_df["DATE_TEMP"] >= start_date) & (temp_df["DATE_TEMP"] <= end_date)
    
    # Séparation des données dans la période et hors période
    in_period = df[mask_period].reset_index(drop=True)
    out_period = df[~mask_period].reset_index(drop=True)
    
    return in_period, out_period
