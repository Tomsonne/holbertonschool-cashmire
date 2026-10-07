from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.categorie import Categorie


def lister_categories(db: Session) -> list[Categorie]:
    """Les catégories prédéfinies, communes à tous, triées par nom (ordre stable)."""
    requete = select(Categorie).order_by(func.lower(Categorie.nom), Categorie.id)
    return list(db.scalars(requete))
