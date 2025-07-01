# CO2 Billing Tool

Application desktop Python pour traiter des fichiers de facturation et y ajouter automatiquement des données d'émission CO2.

## Installation

1. Clonez ce dépôt
2. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
3. Lancez l'application :
   ```bash
   python main.py
   ```

## Fonctionnalités principales
- Import et traitement massif de fichiers CSV
- Mapping automatique avec des facteurs d'émissions CO2
- Interface graphique moderne (PySide6)
- Export CSV ou Excel

## Structure du projet

Voir le dossier `co2tool/` pour la logique métier et l'interface utilisateur.

## Tests

Lancez les tests avec :
```bash
pytest tests/
```
