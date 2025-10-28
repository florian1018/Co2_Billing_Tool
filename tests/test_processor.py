# test_processor.py : Tests pour le module processor
import unittest
import pandas as pd
import os
import sys

# Ajouter le répertoire parent au path pour pouvoir importer les modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) 
from co2tool.core.processor import process_billing_with_co2

class TestProcessor(unittest.TestCase):
    
    def test_deduplicate_co2_config(self):
        """Test de la correction du problème de duplication lors de la fusion avec des facteurs CO2 dupliqués"""
        # Créer un DataFrame de facturation simple
        df_billing = pd.DataFrame([
            {"numero_article": "1234", "quantite": 10, "prix": 100},
            {"numero_article": "5678", "quantite": 5, "prix": 50},
            {"numero_article": "9012", "quantite": 2, "prix": 20}
        ])
        
        # Créer un DataFrame de configuration CO2 avec des doublons
        df_co2 = pd.DataFrame([
            {"numero_article": "1234", "facteur_emission_co2": 2.5},
            {"numero_article": "1234", "facteur_emission_co2": 3.0},  # Doublon avec facteur différent
            {"numero_article": "5678", "facteur_emission_co2": 1.2},
            {"numero_article": "9012", "facteur_emission_co2": 0.8},
            {"numero_article": "9012", "facteur_emission_co2": 0.5}   # Autre doublon
        ])
        
        # Avant la correction, ce test aurait produit un DataFrame résultant avec 5 lignes (3 + 2 doublons)
        # Avec la correction, nous devrions avoir exactement 3 lignes
        
        # Test avec filtrage inactif (garder toutes les lignes)
        result_df = process_billing_with_co2(df_billing.copy(), df_co2.copy(), filter_missing_articles=False)
        
        # Vérifier qu'on a bien le même nombre de lignes que le DataFrame de facturation original
        self.assertEqual(len(result_df), len(df_billing), 
                         f"Le résultat devrait contenir {len(df_billing)} lignes, mais contient {len(result_df)} lignes")
        
        # Vérifier que les facteurs d'émission conservés sont bien les plus élevés pour les articles en doublon
        self.assertEqual(result_df.loc[result_df['numero_article'] == '1234', 'facteur_emission_co2'].iloc[0], 3.0,
                         "Le facteur d'émission le plus élevé (3.0) devrait être conservé pour l'article 1234")
        
        self.assertEqual(result_df.loc[result_df['numero_article'] == '9012', 'facteur_emission_co2'].iloc[0], 0.8,
                         "Le facteur d'émission le plus élevé (0.8) devrait être conservé pour l'article 9012")
        
        # Test avec filtrage actif (ne garder que les lignes avec facteur CO2)
        result_filtered = process_billing_with_co2(df_billing.copy(), df_co2.copy(), filter_missing_articles=True)
        
        # Le résultat devrait toujours avoir 3 lignes puisque tous les articles ont un facteur CO2
        self.assertEqual(len(result_filtered), len(df_billing),
                         f"Le résultat filtré devrait contenir {len(df_billing)} lignes, mais contient {len(result_filtered)} lignes")

    def test_emission_calculation(self):
        """Test du calcul correct des émissions CO2 après fusion"""
        # Créer un DataFrame de facturation avec des prix négatifs (retours)
        df_billing = pd.DataFrame([
            {"numero_article": "1234", "quantite": 10, "prix": 100},   # Facturation normale
            {"numero_article": "5678", "quantite": 5, "prix": -50}    # Retour (prix négatif)
        ])
        
        # Configuration CO2
        df_co2 = pd.DataFrame([
            {"numero_article": "1234", "facteur_emission_co2": 2.0},
            {"numero_article": "5678", "facteur_emission_co2": 3.0}
        ])
        
        # Calculer les émissions
        result_df = process_billing_with_co2(df_billing, df_co2)
        
        # Vérifier les calculs d'émission
        # Article normal: 10 * 2.0 = 20.0
        # Article retourné: 5 * 3.0 * (-1) = -15.0 (facteur inversé pour les retours)
        self.assertEqual(result_df.loc[result_df['numero_article'] == '1234', 'emission_co2'].iloc[0], 20.0,
                         "L'émission pour l'article 1234 devrait être 20.0")
                         
        self.assertEqual(result_df.loc[result_df['numero_article'] == '5678', 'emission_co2'].iloc[0], -15.0,
                         "L'émission pour l'article retourné 5678 devrait être -15.0")

if __name__ == "__main__":
    unittest.main()
