from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import obtenir_session
from app.schemas.categorie import CategorieReponse
from app.services.categories import lister_categories

router = APIRouter()


# Lecture seule : aucune route pour créer, modifier ou supprimer une catégorie au MVP.
@router.get("/categories", response_model=list[CategorieReponse])
def consulter_categories(session: Session = Depends(obtenir_session)):
    return lister_categories(session)
