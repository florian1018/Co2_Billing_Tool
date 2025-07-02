# test_data_utils.py : Tests pour les fonctions de traitement des données et conversion numérique
import unittest
import pandas as pd
from datetime import datetime
from co2tool.utils.data_utils import filter_data_by_date_range, parse_float, parse_date
from co2tool.utils import logger

# Configurer le logger pour les tests
logger.configure_logging(False)


class TestNumericConversion(unittest.TestCase):
    """Tests pour les fonctions de conversion numérique"""
    
    def test_parse_float_valid(self):
        """Test de parse_float avec des valeurs valides"""
        # Test format français avec virgule
        self.assertEqual(parse_float("1,23"), 1.23)
        self.assertEqual(parse_float("1 234,56"), 1234.56)
        
        # Test format international avec point
        self.assertEqual(parse_float("1.23"), 1.23)
        self.assertEqual(parse_float("1,234.56"), 1234.56)
        
        # Test avec espaces et caractères spéciaux
        self.assertEqual(parse_float(" 1.23 "), 1.23)
        self.assertEqual(parse_float("1,234.56 €"), 1234.56)
        self.assertEqual(parse_float("€1,234.56"), 1234.56)
    
    def test_parse_float_invalid(self):
        """Test de parse_float avec des valeurs invalides"""
        # Valeurs non numériques
        self.assertIsNone(parse_float("abc"))
        self.assertIsNone(parse_float(""))
        self.assertIsNone(parse_float(None))
        
        # Valeurs avec caractères mixtes
        self.assertIsNone(parse_float("123abc"))
        self.assertIsNone(parse_float("123-456"))
    
    def test_parse_date(self):
        """Test de parse_date avec différents formats"""
        # Format ISO
        self.assertEqual(parse_date("2024-01-15"), datetime(2024, 1, 15))
        
        # Format français
        self.assertEqual(parse_date("15/01/2024"), datetime(2024, 1, 15))
        
        # Format avec séparateurs différents
        self.assertEqual(parse_date("15-01-2024"), datetime(2024, 1, 15))
        
        # Valeurs invalides
        self.assertIsNone(parse_date("abc"))
        self.assertIsNone(parse_date(""))
        self.assertIsNone(parse_date(None))


class TestDateRangeFiltering(unittest.TestCase):
    """Tests pour le filtrage par plage de dates"""
    
    def setUp(self):
        """Prépare les données de test"""
        # Créer un DataFrame de test avec des dates
        self.df_test = pd.DataFrame({
            'DATE_INVOICE': [
                '2023-01-15', '2023-05-10', '2023-08-22', 
                '2024-01-05', '2024-02-15', '2024-03-20'
            ],
            'AMOUNT': [100, 200, 300, 400, 500, 600]
        })
    
    def test_filter_by_date_range_enabled(self):
        """Test du filtrage activé avec une plage de dates"""
        # Filtrer sur 2024 uniquement
        df_filtered, df_non_period = filter_data_by_date_range(
            self.df_test,
            start_date="2024-01-01",
            end_date="2024-12-31",
            date_col="DATE_INVOICE"
        )
        
        # Vérifier les résultats
        self.assertEqual(len(df_filtered), 3)  # 3 lignes de 2024
        self.assertEqual(len(df_non_period), 3)  # 3 lignes de 2023
        
        # Vérifier les montants pour s'assurer que le bon filtre est appliqué
        self.assertEqual(df_filtered['AMOUNT'].sum(), 1500)  # 400+500+600
        self.assertEqual(df_non_period['AMOUNT'].sum(), 600)  # 100+200+300
    
    def test_filter_by_custom_date_range(self):
        """Test du filtrage avec une plage de dates personnalisée"""
        # Filtrer sur une période spécifique
        df_filtered, df_non_period = filter_data_by_date_range(
            self.df_test,
            start_date="2023-05-01",
            end_date="2024-02-01",
            date_col="DATE_INVOICE"
        )
        
        # Vérifier les résultats
        self.assertEqual(len(df_filtered), 3)  # 3 lignes dans la période (mai 2023 à février 2024)
        self.assertEqual(len(df_non_period), 3)  # 3 lignes hors période
        
        # Vérifier les montants spécifiques
        self.assertEqual(df_filtered['AMOUNT'].sum(), 900)  # 200+300+400
    
    def test_filter_disabled(self):
        """Test quand le filtrage est désactivé"""
        # Sans filtrage (dates vides)
        df_filtered, df_non_period = filter_data_by_date_range(
            self.df_test,
            start_date="",
            end_date="",
            date_col="DATE_INVOICE"
        )
        
        # Tout doit être inclus dans df_filtered
        self.assertEqual(len(df_filtered), 6)
        self.assertEqual(df_non_period, None)  # Pas de données hors période
    
    def test_filter_with_missing_date_column(self):
        """Test avec une colonne de date manquante"""
        # DataFrame sans colonne DATE_INVOICE
        df_bad = pd.DataFrame({'AMOUNT': [100, 200, 300]})
        
        # Le filtrage devrait retourner le DataFrame d'origine sans modification
        df_filtered, df_non_period = filter_data_by_date_range(
            df_bad,
            start_date="2024-01-01",
            end_date="2024-12-31",
            date_col="DATE_INVOICE"
        )
        
        self.assertEqual(len(df_filtered), 3)  # Toutes les lignes
        self.assertEqual(df_non_period, None)  # Pas de données hors période


if __name__ == '__main__':
    unittest.main()
