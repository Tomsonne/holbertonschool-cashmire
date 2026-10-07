from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.authentification import utilisateur_courant
from app.db.session import get_db
from app.models.utilisateur import Utilisateur
from app.schemas.depense import DepenseEntree, DepenseSortie
from app.services.depenses import creer_depense

router = APIRouter()


@router.post("", response_model=DepenseSortie, status_code=201)
def creation_depense(
    donnees: DepenseEntree,
    utilisateur: Utilisateur = Depends(utilisateur_courant),
    db: Session = Depends(get_db),
) -> DepenseSortie:
    return creer_depense(db, utilisateur, donnees)
