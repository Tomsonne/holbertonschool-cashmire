"""Dépendance FastAPI de l'utilisateur connecté.

PROVISOIRE : cette version refuse toute requête (401). Elle sera remplacée par celle de #9
(lecture et vérification du JWT dans le cookie). Les routes privées dépendent de ce nom ;
les tests le remplacent par un utilisateur de test avec `app.dependency_overrides`.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.erreurs import ErreurApi
from app.db.session import get_db
from app.models.utilisateur import Utilisateur


def utilisateur_courant(db: Session = Depends(get_db)) -> Utilisateur:
    raise ErreurApi(401, "Authentification requise.")
