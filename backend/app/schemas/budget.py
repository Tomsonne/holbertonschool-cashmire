import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BudgetCreation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categorie_id: UUID
    montant_limite: Decimal
    mois: str
    seuil_alerte_pct: Annotated[int, Field(strict=True, ge=1, le=100)] = 80

    @field_validator("montant_limite", mode="before")
    @classmethod
    def montant_decimal_depuis_chaine(cls, value: object) -> Decimal:
        if not isinstance(value, str):
            raise ValueError("doit être une chaîne décimale")
        try:
            montant = Decimal(value)
        except (InvalidOperation, ValueError):
            raise ValueError("doit être un nombre décimal valide") from None
        if not montant.is_finite():
            raise ValueError("doit être un nombre décimal fini")
        if montant <= 0:
            raise ValueError("doit être supérieur à 0")
        if montant.as_tuple().exponent < -2:
            raise ValueError("ne peut pas dépasser deux décimales")
        if montant >= Decimal("10000000000"):
            raise ValueError("dépasse la limite autorisée")
        return montant

    @field_validator("mois")
    @classmethod
    def mois_valide(cls, value: str) -> str:
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
            raise ValueError("doit respecter le format AAAA-MM")
        try:
            date.fromisoformat(f"{value}-01")
        except ValueError:
            raise ValueError("doit être un mois valide") from None
        return value

    @property
    def periode_mois(self) -> date:
        return date.fromisoformat(f"{self.mois}-01")


class CategorieResume(BaseModel):
    id: UUID
    nom: str


class BudgetResponse(BaseModel):
    id: UUID
    categorie: CategorieResume
    mois: str
    montant_limite: str
    depense: str
    reste: str
    pourcentage: Decimal
    seuil_alerte_pct: int
    statut: str
