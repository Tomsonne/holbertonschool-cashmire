import re
from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from app.schemas.montant import Montant, MontantPositif
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator


class BudgetCreation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categorie_id: UUID
    montant_limite: MontantPositif
    mois: str
    seuil_alerte_pct: Annotated[int, Field(strict=True, ge=1, le=100)] = 80

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


MoisBudget = Annotated[str, AfterValidator(BudgetCreation.mois_valide)]


class BudgetModification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    montant_limite: MontantPositif | None = None
    seuil_alerte_pct: Annotated[int, Field(strict=True, ge=1, le=100)] | None = None

    @field_validator("montant_limite", mode="before")
    @classmethod
    def montant_non_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("doit être un montant positif")
        return value

    @field_validator("seuil_alerte_pct", mode="before")
    @classmethod
    def seuil_non_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("doit être un entier entre 1 et 100")
        return value

    @model_validator(mode="after")
    def au_moins_un_champ(self):
        if not self.model_fields_set:
            raise ValueError("au moins un champ doit être fourni")
        return self


class CategorieResume(BaseModel):
    id: UUID
    nom: str


class BudgetResponse(BaseModel):
    id: UUID
    categorie: CategorieResume
    mois: str
    montant_limite: MontantPositif
    depense: Montant
    reste: Montant
    pourcentage: Decimal
    seuil_alerte_pct: int
    statut: str

    @field_serializer("pourcentage")
    def serialiser_pourcentage(self, value: Decimal) -> float:
        return float(value)
