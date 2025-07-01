# processor.py : Agrégation, filtrage, jointure CO2
import pandas as pd
from rich.console import Console
from typing import List
from co2tool.core.config import CO2ConfigFile

console = Console()

def process_billing_with_co2(df_billing: pd.DataFrame, df_co2: pd.DataFrame) -> pd.DataFrame:
    """
    Fusionne les factures avec la config CO2 (DataFrame), filtre et calcule les émissions.
    Toutes les colonnes de la config CO2 (ex: CM, Nom_Cat) sont propagées dans le résultat.
    """
    # Cast pour jointure robuste
    df_billing["numero_article"] = df_billing["numero_article"].astype(str)
    df_co2["numero_article"] = df_co2["numero_article"].astype(str)
    # Jointure gauche
    merged = pd.merge(df_billing, df_co2, on="numero_article", how="left")
    avant_filtrage = len(merged)
    # Filtrer uniquement les lignes avec facteur CO2 non nul
    filtered = merged[merged["facteur_emission_co2"].notnull()].copy()
    apres_filtrage = len(filtered)
    # Calcul émissions
    # Log des valeurs non convertibles en float pour facteur_emission_co2
    not_float_mask = filtered["facteur_emission_co2"].apply(lambda x: pd.api.types.is_number(x) or (isinstance(x, float) or isinstance(x, int))) == False
    try:
        filtered["facteur_emission_co2"] = filtered["facteur_emission_co2"].astype(float)
    except Exception as e:
        for idx, val in filtered.loc[~filtered["facteur_emission_co2"].apply(lambda x: isinstance(x, float) or isinstance(x, int)), "facteur_emission_co2"].items():
            try:
                float(val)
            except Exception:
                console.log(f"[red]Ligne {idx+2} : facteur_emission_co2 non convertible : '{val}'\nContenu complet : {filtered.loc[idx].to_dict()}")
        raise
    filtered["quantite"] = filtered["quantite"].astype(float)
    filtered["emission_co2"] = filtered["quantite"] * filtered["facteur_emission_co2"]
    console.log(f"[cyan]Factures fusionnées : {avant_filtrage} lignes, après filtrage CO2 : {apres_filtrage} lignes")
    return filtered.reset_index(drop=True)

