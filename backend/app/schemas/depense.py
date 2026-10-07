import uuid
from datetime import date, timedelta
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator, model_validator

from app.schemas.categorie import CategorieSortie
from app.schemas.montant import Montant, MontantPositif

DATE_MINIMALE = date(2000, 1, 1)

Libelle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


def verifier_la_date_de_depense(valeur: date) -> date:
    # Un jour de tolérance sur « aujourd'hui » : le serveur peut avoir un jour de retard sur
    # le fuseau horaire de l'utilisateur. Une dépense a déjà eu lieu : le futur est refusé.
    if not DATE_MINIMALE <= valeur <= date.today() + timedelta(days=1):
        raise ValueError("Date hors de la période autorisée.")
    return valeur


class DepenseEntree(BaseModel):
    """Corps de la création d'une dépense. Le propriétaire n'en fait pas partie : il vient du JWT."""

    montant: MontantPositif
    libelle: Libelle
    date_depense: date
    categorie_id: uuid.UUID

    @field_validator("date_depense")
    @classmethod
    def verifier_la_date(cls, valeur: date) -> date:
        return verifier_la_date_de_depense(valeur)


class DepenseModification(BaseModel):
    """Corps du PATCH : seuls les champs envoyés sont modifiés, avec les règles de la création.

    Comme pour les budgets : un champ inconnu (par exemple `utilisateur_id`) est refusé, un champ
    présent ne peut pas valoir `null`, et au moins un champ est obligatoire.
    """

    model_config = ConfigDict(extra="forbid")

    montant: MontantPositif | None = None
    libelle: Libelle | None = None
    date_depense: date | None = None
    categorie_id: uuid.UUID | None = None

    @field_validator("montant", "libelle", "date_depense", "categorie_id", mode="before")
    @classmethod
    def refuser_null(cls, valeur: object) -> object:
        if valeur is None:
            raise ValueError("Une valeur est obligatoire.")
        return valeur

    @field_validator("date_depense")
    @classmethod
    def verifier_la_date(cls, valeur: date) -> date:
        return verifier_la_date_de_depense(valeur)

    @model_validator(mode="after")
    def au_moins_un_champ(self):
        if not self.model_fields_set:
            raise ValueError("Au moins un champ doit être fourni.")
        return self


class DepenseSortie(BaseModel):
    """Dépense renvoyée par l'API : jamais d'identifiant d'utilisateur."""

    id: uuid.UUID
    montant: Montant
    libelle: str
    date_depense: date
    categorie: CategorieSortie


class ListeDepensesSortie(BaseModel):
    """Une page de dépenses. `total` compte toutes les dépenses du filtre, avant la pagination."""

    elements: list[DepenseSortie]
    total: int
