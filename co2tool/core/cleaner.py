import re
import pandas as pd
from typing import Optional

def try_parse_float(val: str) -> Optional[float]:
    """
    Tente de convertir une valeur en float, même si elle contient des séparateurs ou du texte.
    Retourne None si la conversion est impossible.
    """
    if pd.isnull(val):
        return None
    s = str(val).strip().replace("\u202f", "").replace("\xa0", "")
    s = s.replace(" ", "")
    # Cas typiques : "1,100.000", "1 000,23", etc.
    # On supprime les espaces, puis on tente de détecter le format
    # 1. Si virgule comme séparateur de milliers, on l'enlève
    if re.match(r"^\d{1,3}(,\d{3})*(\.\d+)?$", s):
        s = s.replace(",", "")
    # 2. Si virgule comme séparateur décimal
    elif s.count(",") == 1 and s.count(".") == 0:
        s = s.replace(",", ".")
    # 3. Si plusieurs points, on garde le dernier comme décimal
    elif s.count(".") > 1:
        parts = s.split(".")
        s = "".join(parts[:-1]) + "." + parts[-1]
    # 4. Texte pur ou mélange
    try:
        return float(s)
    except Exception:
        return None

def clean_quantity_column(df: pd.DataFrame, col: str = "quantite") -> pd.DataFrame:
    """
    Nettoie la colonne quantité d'un DataFrame : tente de convertir chaque valeur en float intelligemment.
    Remplace les valeurs non convertibles par None (ou NaN).
    Retourne le DataFrame modifié.
    """
    df = df.copy()
    df[col] = df[col].apply(try_parse_float)
    return df
