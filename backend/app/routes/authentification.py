from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.utilisateur import InscriptionEntree, UtilisateurSortie
from app.services.authentification import inscrire

router = APIRouter()


@router.post("/inscription", response_model=UtilisateurSortie, status_code=201)
def inscription(donnees: InscriptionEntree, db: Session = Depends(get_db)) -> UtilisateurSortie:
    # L'inscription ne connecte pas l'utilisateur : ni cookie ni JWT (voir la connexion).
    return inscrire(db, donnees)
