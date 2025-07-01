# config.py : Modèles Pydantic pour validation
from pydantic import BaseModel, Field, validator, StrictStr, StrictFloat, StrictInt
from typing import Optional

class CO2ConfigEntry(BaseModel):
    numero_article: StrictStr | StrictInt = Field(..., description="Numéro d'article")
    facteur_emission_co2: StrictFloat = Field(..., ge=0, description="Facteur d'émission CO2 (>=0)")

class CO2ConfigFile(BaseModel):
    entries: list[CO2ConfigEntry]

class BillingLine(BaseModel):
    numero_article: StrictStr | StrictInt = Field(..., description="Numéro d'article")
    quantite: StrictFloat = Field(..., ge=0, description="Quantité (>=0)")
    prix: StrictFloat = Field(..., ge=0, description="Prix (>=0)")
    # D'autres colonnes métier peuvent être ajoutées dynamiquement
    
    class Config:
        extra = "allow"  # Autorise d'autres champs métier, mais valide les principaux
