import uuid

from pydantic import BaseModel, ConfigDict


class CategorieSortie(BaseModel):
    """Catégorie prédéfinie, en lecture seule : seuls l'identifiant et le nom sont exposés."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nom: str
