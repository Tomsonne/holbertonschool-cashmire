import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.authentification import utilisateur_courant
from app.db.session import get_db
from app.models.utilisateur import Utilisateur
from app.schemas.budget import MoisBudget
from app.schemas.depense import (
    DepenseEntree,
    DepenseModification,
    DepenseSortie,
    ListeDepensesSortie,
)
from app.services.depenses import (
    creer_depense,
    lister_depenses,
    modifier_depense,
    obtenir_depense,
    supprimer_depense,
)

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


@router.patch("/{depense_id}", response_model=DepenseSortie)
def modification_depense(
    depense_id: uuid.UUID,
    donnees: DepenseModification,
    utilisateur: Utilisateur = Depends(utilisateur_courant),
    db: Session = Depends(get_db),
) -> DepenseSortie:
    return modifier_depense(db, utilisateur, depense_id, donnees)


@router.delete("/{depense_id}", status_code=204, response_model=None)
def suppression_depense(
    depense_id: uuid.UUID,
    utilisateur: Utilisateur = Depends(utilisateur_courant),
    db: Session = Depends(get_db),
) -> Response:
    supprimer_depense(db, utilisateur, depense_id)
    return Response(status_code=204)
