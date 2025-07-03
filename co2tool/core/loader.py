# loader.py : Chargement et validation des CSV
import pandas as pd
from pathlib import Path
from rich.console import Console
from typing import List, Tuple, Dict, Any
from co2tool.core.config import CO2ConfigEntry, CO2ConfigFile, BillingLine
from co2tool.utils.data_utils import parse_float, load_csv_with_encoding, clean_quantity_column
from pydantic import ValidationError

console = Console()

def load_billing_csv_files(file_paths: List[Path]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Charge et concatène plusieurs fichiers CSV de facturation en un seul DataFrame.
    Retourne aussi un rapport détaillé des fichiers inclus/exclus.
    """
    dataframes = []
    included_files = []
    excluded_files = []
    
    # Mapping standard des colonnes externes vers colonnes internes
    column_mapping = {
        "ID_MATERIAL": "numero_article",
        "QUANTITY": "quantite",
        "AMOUNT_NET": "prix"
    }
    
    # Colonnes requises après mapping
    required_cols = {"numero_article", "quantite", "prix"}
    
    for file_path in file_paths:
        try:
            # Utiliser notre fonction centralisée pour gérer les différents encodages
            df = load_csv_with_encoding(
                file_path, 
                sep=';', 
                dtype=str, 
                engine="pyarrow"
            )
            
            # Vérifier si le fichier est déjà au format traité (contient directement les colonnes mappées)
            if required_cols.issubset(df.columns):
                # Le fichier contient déjà les colonnes mappées, pas besoin de vérifier les colonnes originales
                console.log(f"[blue]Fichier déjà traité détecté : {file_path}")
            else:
                # Vérification des colonnes originales nécessaires
                missing = [col for col in column_mapping if col not in df.columns]
                if missing:
                    raise ValueError(f"Colonnes requises manquantes {missing}")
                    
                # Mapping des colonnes vers les noms standards
                df = df.rename(columns={col: column_mapping.get(col, col) for col in df.columns if col in column_mapping})
                
                # Vérification après mapping
                if not required_cols.issubset(df.columns):
                    raise ValueError(f"Colonnes internes requises manquantes {required_cols - set(df.columns)}")
            
            # Nettoyage des numéros d'article (suppression des zéros initiaux)
            from co2tool.utils.data_utils import clean_numero_article_column
            df = clean_numero_article_column(df, col="numero_article")
            # Nettoyage des colonnes numériques
            df = clean_quantity_column(df, col="quantite")
            
            # Nettoyage de la colonne prix
            if "prix" in df.columns:
                df["prix"] = df["prix"].apply(parse_float)
            
            # Ajout du fichier source comme colonne
            df["SOURCE_FILE"] = str(file_path)
            
            # Log des statistiques
            console.log(f"[green]Fichier chargé et mappé : {file_path} ({len(df)} lignes)")
            
            # Exclure les lignes avec des valeurs non convertibles
            for col in ["prix", "quantite"]:
                if col in df.columns:
                    invalid_mask = df[col].isna()
                    if invalid_mask.any():
                        invalid_count = invalid_mask.sum()
                        console.log(f"[yellow]{invalid_count} lignes avec valeurs non convertibles dans '{col}'")
                        df = df[~invalid_mask].copy()
            
            dataframes.append(df)
            included_files.append(str(file_path))
            
        except Exception as e:
            excluded_files.append({"file": str(file_path), "reason": str(e)})
            console.log(f"[red]Fichier ignoré : {file_path} - Raison : {e}")
    
    if not dataframes:
        raise ValueError("Aucun fichier CSV valide chargé.")
        
    df_all = pd.concat(dataframes, ignore_index=True)
    
    rapport = {
        "fichiers_inclus": included_files,
        "fichiers_exclus": excluded_files,
        "nb_fichiers_inclus": len(included_files),
        "nb_fichiers_exclus": len(excluded_files)
    }
    
    return df_all, rapport

def validate_billing_lines(df: pd.DataFrame) -> List[BillingLine]:
    """
    Valide chaque ligne du DataFrame comme une BillingLine Pydantic.
    """
    validated = []
    for idx, row in df.iterrows():
        try:
            entry = BillingLine(**row.to_dict())
            validated.append(entry)
        except ValidationError as ve:
            console.log(f"[yellow]Ligne {idx} invalide : {ve}")
            continue
    if not validated:
        raise ValueError("Aucune ligne de facturation valide.")
    return validated

def load_co2_config_csv(config_path: Path) -> pd.DataFrame:
    """
    Charge et valide un fichier de configuration CO2.
    Retourne un DataFrame avec toutes les colonnes, incluant les colonnes supplémentaires éventuelles.
    """
    try:
        # Utiliser la fonction centralisée pour charger le CSV
        df = load_csv_with_encoding(config_path, sep=';', dtype=str, engine="pyarrow")
        
        # Mapping possible des colonnes config CO2
        mapping_possibles = [
            {"Num_art": "numero_article", "FE": "facteur_emission_co2"},
            {"numero_article": "numero_article", "facteur_emission_co2": "facteur_emission_co2"}
        ]
        
        # Appliquer le premier mapping qui correspond
        for mapping in mapping_possibles:
            if set(mapping.keys()).issubset(set(df.columns)):
                df = df.rename(columns=mapping)
                console.log(f"[green]Mapping config CO2 utilisé : {mapping}")
                break
        else:
            raise ValueError(f"Colonnes attendues : ['numero_article', 'facteur_emission_co2'] ou ['Num_art', 'FE'], trouvé : {list(df.columns)}")
        
        # Nettoyage des numéros d'article (suppression des zéros initiaux)
        from co2tool.utils.data_utils import clean_numero_article_column
        df = clean_numero_article_column(df, col="numero_article")
        # Conversion du facteur d'émission avec la fonction utilitaire
        df["facteur_emission_co2"] = df["facteur_emission_co2"].apply(parse_float)
        
        # Filtrer les lignes avec des valeurs nulles
        df = df[df["facteur_emission_co2"].notnull() & df["numero_article"].notnull()]
        
        if df.empty:
            raise ValueError("Aucune entrée de configuration CO2 valide.")
            
        return df.reset_index(drop=True)
        
    except Exception as e:
        console.log(f"[red]Erreur lors du chargement du fichier de configuration CO2 : {e}")
        raise
