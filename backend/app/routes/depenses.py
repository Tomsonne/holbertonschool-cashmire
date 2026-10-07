import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.authentification import utilisateur_courant
from app.db.session import get_db
from app.models.utilisateur import Utilisateur
from app.schemas.budget import MoisBudget
from app.schemas.depense import DepenseEntree, DepenseSortie, ListeDepensesSortie
from app.services.depenses import creer_depense, lister_depenses, obtenir_depense

router = APIRouter()


@router.post("", response_model=DepenseSortie, status_code=201)
def creation_depense(
    donnees: DepenseEntree,
    utilisateur: Utilisateur = Depends(utilisateur_courant),
    db: Session = Depends(get_db),
) -> DepenseSortie:
    return creer_depense(db, utilisateur, donnees)


@router.get("", response_model=ListeDepensesSortie)
def liste_depenses(
    mois: MoisBudget | None = None,
    categorie_id: uuid.UUID | None = None,
    limite: Annotated[int, Query(ge=1, le=100)] = 20,
    decalage: Annotated[int, Query(ge=0)] = 0,
    utilisateur: Utilisateur = Depends(utilisateur_courant),
    db: Session = Depends(get_db),
) -> ListeDepensesSortie:
    return lister_depenses(db, utilisateur, mois, categorie_id, limite, decalage)


@router.get("/{depense_id}", response_model=DepenseSortie)
def detail_depense(
    depense_id: uuid.UUID,
    utilisateur: Utilisateur = Depends(utilisateur_courant),
    db: Session = Depends(get_db),
) -> DepenseSortie:
    return obtenir_depense(db, utilisateur, depense_id)
