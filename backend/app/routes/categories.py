from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.authentification import utilisateur_courant
from app.db.session import get_db
from app.models.utilisateur import Utilisateur
from app.schemas.categorie import CategorieSortie
from app.services.categories import lister_categories

router = APIRouter()


# Lecture seule : aucune route pour créer, modifier ou supprimer une catégorie au MVP.
@router.get("", response_model=list[CategorieSortie])
def consultation_categories(
    _utilisateur: Utilisateur = Depends(utilisateur_courant),
    db: Session = Depends(get_db),
) -> list[CategorieSortie]:
    return lister_categories(db)
