import uuid
from datetime import date, timedelta
from typing import Annotated

from pydantic import BaseModel, StringConstraints, field_validator

from app.schemas.categorie import CategorieSortie
from app.schemas.montant import Montant, MontantPositif

DATE_MINIMALE = date(2000, 1, 1)


class DepenseEntree(BaseModel):
    """Corps de la création d'une dépense. Le propriétaire n'en fait pas partie : il vient du JWT."""

    montant: MontantPositif
    libelle: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    date_depense: date
    categorie_id: uuid.UUID

    @field_validator("date_depense")
    @classmethod
    def verifier_la_date(cls, valeur: date) -> date:
        # Un jour de tolérance sur « aujourd'hui » : le serveur peut avoir un jour de retard sur
        # le fuseau horaire de l'utilisateur. Une dépense a déjà eu lieu : le futur est refusé.
        if not DATE_MINIMALE <= valeur <= date.today() + timedelta(days=1):
            raise ValueError("Date hors de la période autorisée.")
        return valeur


class DepenseSortie(BaseModel):
    """Dépense renvoyée par l'API : jamais d'identifiant d'utilisateur."""

    id: uuid.UUID
    montant: Montant
    libelle: str
    date_depense: date
    categorie: CategorieSortie
