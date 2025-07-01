# loader.py : Chargement et validation des CSV
import pandas as pd
from pathlib import Path
from rich.console import Console
from typing import List
from co2tool.core.config import CO2ConfigEntry, CO2ConfigFile, BillingLine
from pydantic import ValidationError

console = Console()

def load_billing_csv_files(file_paths: List[Path]):
    """
    Charge et concatène plusieurs fichiers CSV de facturation en un seul DataFrame.
    Retourne aussi un rapport détaillé des fichiers inclus/exclus.
    """
    dataframes = []
    included_files = []
    excluded_files = []
    for file_path in file_paths:
        try:
            df = pd.read_csv(file_path, dtype=str, engine="pyarrow", sep=';', encoding='utf-8')
        except UnicodeDecodeError:
            console.log(f"[yellow]Encodage utf-8 échoué pour {file_path}, tentative avec 'latin1'.")
            df = pd.read_csv(file_path, dtype=str, engine="pyarrow", sep=';', encoding='latin1')
        # Mapping des colonnes du CSV réel vers les noms internes
            column_mapping = {
                "ID_MATERIAL": "numero_article",
                "QUANTITY": "quantite",
                "AMOUNT_NET": "prix"
            }
            missing = [col for col in column_mapping if col not in df.columns]
            if missing:
                raise ValueError(f"Colonnes requises manquantes {missing}")
            df = df.rename(columns=column_mapping)
            # Nettoyage intelligent de la colonne quantité (conversion texte->float si possible)
            from co2tool.core.cleaner import clean_quantity_column
            df = clean_quantity_column(df, col="quantite")
            # Validation des colonnes minimales internes
            required_cols = {"numero_article", "quantite", "prix"}
            if not required_cols.issubset(df.columns):
                raise ValueError(f"Colonnes internes requises manquantes {required_cols - set(df.columns)}")
            # DEBUG : Vérification stricte des types convertibles avec diagnostic
            for col in ["prix", "quantite"]:
                if col in df.columns:
                    # Diagnostic des valeurs problématiques
                    problematic_mask = pd.Series([False] * len(df))
                    for idx, val in df[col].items():
                        try:
                            float(str(val))
                        except ValueError:
                            problematic_mask.iloc[idx] = True
                            console.log(f"[red]DIAGNOSTIC - Fichier {file_path}, ligne {idx+2}, colonne '{col}': '{val}' (type: {type(val).__name__})")
                    if problematic_mask.any():
                        console.log(f"[yellow]DIAGNOSTIC - {problematic_mask.sum()} valeurs non convertibles trouvées dans '{col}'")
                        # Exclure ces lignes pour continuer le traitement
                        df = df[~problematic_mask].copy()
                        console.log(f"[blue]Lignes restantes après nettoyage : {len(df)}")
                    # Test final de conversion
                    try:
                        df[col].astype(float)
                        console.log(f"[green]Colonne '{col}' maintenant convertible en float")
                    except Exception as e:
                        raise ValueError(f"Colonne '{col}' encore non convertible : {e}")
            # Log des types de colonnes et des premières lignes
            console.log(f"[blue]Types de colonnes pour {file_path}:\n{df.dtypes}")
            console.log(f"[blue]Premières lignes de {file_path}:\n{df.head(3)}")
            # Vérification stricte des types convertibles
            for col in ["prix", "quantite"]:
                if col in df.columns:
                    try:
                        df[col].astype(float)
                    except Exception as e:
                        raise ValueError(f"Colonne '{col}' non convertible en float : {e}")
            dataframes.append(df)
            included_files.append(str(file_path))
            console.log(f"[green]Fichier chargé et mappé : {file_path} ({len(df)} lignes)")
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

def load_co2_config_csv(config_path: Path) -> CO2ConfigFile:
    """
    Charge et valide un fichier de configuration CO2 (2 colonnes).
    """
    try:
        df = pd.read_csv(config_path, dtype=str, engine="pyarrow", sep=';')
        # Mapping possible des colonnes config CO2
        mapping_possibles = [
            {"Num_art": "numero_article", "FE": "facteur_emission_co2"},
            {"numero_article": "numero_article", "facteur_emission_co2": "facteur_emission_co2"}
        ]
        for mapping in mapping_possibles:
            if set(mapping.keys()).issubset(set(df.columns)):
                df = df.rename(columns=mapping)
                console.log(f"[green]Mapping config CO2 utilisé : {mapping}")
                break
        else:
            raise ValueError(f"Colonnes attendues : ['numero_article', 'facteur_emission_co2'] ou ['Num_art', 'FE'], trouvé : {list(df.columns)}")
        # Nettoyage/parse du facteur d'émission, conservation des colonnes additionnelles
        def parse_float(val):
            try:
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
        # Exclure les lignes où une virgule est présente dans le facteur d'émission
        mask = df["facteur_emission_co2"].astype(str).str.contains(",")
        if mask.any():
            for idx, val in df.loc[mask, "facteur_emission_co2"].items():
                console.log(f"[yellow]Config CO2 : ligne {idx+2} colonne 'facteur_emission_co2' valeur suspecte : '{val}' (virgule détectée, ligne ignorée)")
        df = df[~mask].copy()
        # Log des valeurs non convertibles en float
        not_float_mask = df["facteur_emission_co2"].apply(lambda x: parse_float(x) is None)
        if not_float_mask.any():
            for idx, val in df.loc[not_float_mask, "facteur_emission_co2"].items():
                console.log(f"[red]Config CO2 : ligne {idx+2} colonne 'facteur_emission_co2' valeur non convertible en float : '{val}' (ligne ignorée)")
        df["facteur_emission_co2"] = df["facteur_emission_co2"].apply(parse_float)
        # On ne valide plus avec Pydantic ici, on retourne le DataFrame enrichi (toutes colonnes)
        df = df[df["facteur_emission_co2"].notnull() & df["numero_article"].notnull()]
        if df.empty:
            raise ValueError("Aucune entrée de configuration CO2 valide.")
        return df.reset_index(drop=True)
    except Exception as e:
        console.log(f"[red]Erreur lors du chargement du fichier de configuration CO2 : {e}")
        raise
