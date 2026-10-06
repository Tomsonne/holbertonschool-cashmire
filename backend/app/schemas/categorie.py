from uuid import UUID
from pydantic import BaseModel, ConfigDict


class CategorieReponse(BaseModel):
    """Catégorie prédéfinie, en lecture seule : seuls l'identifiant et le nom sont exposés."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nom: str
