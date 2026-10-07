import uuid
from datetime import datetime
from typing import Annotated

from email_validator import validate_email
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


def normaliser_email(valeur: str) -> str:
    """Espaces retirés, minuscules, syntaxe vérifiée (partagé par l'inscription et la connexion)."""
    # Un EmailNotValidError est un ValueError : Pydantic le convertit en erreur 422.
    valide = validate_email(valeur.strip().lower(), check_deliverability=False)
    return valide.normalized.lower()


class InscriptionEntree(BaseModel):
    email: str
    # Le mot de passe n'est ni nettoyé ni tronqué : les espaces font partie du secret.
    mot_de_passe: str = Field(min_length=10, max_length=128)
    nom_affichage: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]

    @field_validator("email")
    @classmethod
    def _normaliser_email(cls, valeur: str) -> str:
        return normaliser_email(valeur)


class ConnexionEntree(BaseModel):
    email: str
    # Ni minimum ni règle de composition (la politique de l'inscription ne s'applique pas ici),
    # et jamais nettoyé ni tronqué. Le maximum borne seulement le coût du hachage.
    mot_de_passe: str = Field(max_length=128)

    @field_validator("email")
    @classmethod
    def _normaliser_email(cls, valeur: str) -> str:
        return normaliser_email(valeur)


class UtilisateurSortie(BaseModel):
    """Utilisateur renvoyé par l'API : jamais de mot de passe ni de hash."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    nom_affichage: str
    date_creation: datetime
