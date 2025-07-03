# processor.py : Agrégation, filtrage, jointure CO2
import pandas as pd
from typing import List
from co2tool.core.config import CO2ConfigFile
from co2tool.utils import logger

def process_billing_with_co2(df_billing: pd.DataFrame, df_co2: pd.DataFrame, filter_missing_articles: bool = True) -> pd.DataFrame:
    """
    Fusionne les factures avec la config CO2 (DataFrame), applique les facteurs CO2 et calcule les émissions.
    Gère également le cas où le fichier d'entrée contient déjà des colonnes de traitement CO2.
    
    Args:
        df_billing: DataFrame des factures
        df_co2: DataFrame de la configuration CO2
        filter_missing_articles: Si True, supprime les lignes dont le numéro d'article n'est pas dans la config CO2
                                Si False, conserve toutes les lignes, même sans correspondance CO2
    
    Returns:
        DataFrame traité avec calcul des émissions CO2
    """
    # Vérifier si le fichier contient déjà des colonnes de traitement CO2
    fichier_deja_traite = "facteur_emission_co2" in df_billing.columns
    
    if fichier_deja_traite:
        logger.info("Fichier déjà traité détecté, réapplication des facteurs CO2")
        # Supprimer les colonnes de traitement CO2 existantes pour éviter les doublons
        colonnes_a_supprimer = ["facteur_emission_co2", "emission_co2"]
        df_billing = df_billing.drop(columns=[col for col in colonnes_a_supprimer if col in df_billing.columns])
    
    # Cast pour jointure robuste
    df_billing["numero_article"] = df_billing["numero_article"].astype(str)
    df_co2["numero_article"] = df_co2["numero_article"].astype(str)
    
    # Jointure gauche pour conserver toutes les factures
    merged = pd.merge(df_billing, df_co2, on="numero_article", how="left")
    avant_filtrage = len(merged)
    
    # Vérifier si la colonne facteur_emission_co2 existe après la fusion
    if "facteur_emission_co2" not in merged.columns:
        # Si la colonne n'existe pas, c'est que la configuration CO2 n'a pas cette colonne
        # Ajouter une colonne vide pour éviter les erreurs
        logger.warning("La colonne 'facteur_emission_co2' n'existe pas dans la configuration CO2")
        merged["facteur_emission_co2"] = 0
        result_df = merged.copy()
    else:
        # Traitement normal avec la colonne facteur_emission_co2
        if filter_missing_articles:
            # Mode standard: on filtre pour ne garder que les lignes avec facteur CO2 non nul
            result_df = merged[merged["facteur_emission_co2"].notnull()].copy()
            apres_filtrage = len(result_df)
            logger.info(f"Filtrage actif: {avant_filtrage-apres_filtrage} lignes sans correspondance CO2 supprimées")
        else:
            # Mode nouveau: on garde toutes les lignes, même celles sans facteur CO2
            result_df = merged.copy()
            nb_sans_co2 = merged["facteur_emission_co2"].isnull().sum()
            logger.info(f"Filtrage inactif: conservation de {nb_sans_co2} lignes sans correspondance CO2")
    
    # Remplacer les valeurs nulles par 0 pour le calcul des émissions
    result_df["facteur_emission_co2"] = result_df["facteur_emission_co2"].fillna(0)
    
    # Log des valeurs non convertibles en float pour facteur_emission_co2
    try:
        result_df["facteur_emission_co2"] = result_df["facteur_emission_co2"].astype(float)
    except Exception as e:
        for idx, val in result_df.loc[~result_df["facteur_emission_co2"].apply(
            lambda x: isinstance(x, float) or isinstance(x, int) or pd.isna(x)), "facteur_emission_co2"].items():
            try:
                float(val)
            except Exception:
                logger.error(f"Ligne {idx+2} : facteur_emission_co2 non convertible : '{val}'")
                logger.debug(f"Contenu complet de la ligne: {result_df.loc[idx].to_dict()}")
        raise
    
    # Calcul des émissions
    result_df["quantite"] = result_df["quantite"].astype(float)
    
    # S'assurer que la colonne prix est au format numérique
    if "prix" in result_df.columns:
        result_df["prix"] = result_df["prix"].astype(float)
        
        # Appliquer un facteur négatif si le prix est négatif (retour)
        # Créer une colonne temporaire pour le signe
        result_df["signe_prix"] = result_df["prix"].apply(lambda x: -1 if x < 0 else 1)
        
        # Appliquer le signe au facteur d'émission
        result_df["facteur_emission_co2_ajuste"] = result_df["facteur_emission_co2"] * result_df["signe_prix"]
        
        # Calcul des émissions avec le facteur ajusté
        result_df["emission_co2"] = result_df["quantite"] * result_df["facteur_emission_co2_ajuste"]
        
        # Supprimer les colonnes temporaires
        result_df = result_df.drop(columns=["signe_prix", "facteur_emission_co2_ajuste"])
        
        # Log des retours détectés
        nb_retours = (result_df["prix"] < 0).sum()
        if nb_retours > 0:
            logger.info(f"Détection de {nb_retours} lignes de retour (prix négatif) avec facteur d'émission inversé")
    else:
        # Si la colonne prix n'est pas disponible, calcul standard
        logger.warning("Colonne 'prix' non disponible, impossible de détecter les retours")
        result_df["emission_co2"] = result_df["quantite"] * result_df["facteur_emission_co2"]
    
    if filter_missing_articles:
        logger.info(f"Factures traitées: {avant_filtrage} lignes initiales, {len(result_df)} lignes après filtrage CO2")
    else:
        logger.info(f"Factures traitées: {avant_filtrage} lignes, aucun filtrage appliqué")
        
    return result_df.reset_index(drop=True)

