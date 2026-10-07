from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.authentification import utilisateur_courant
from app.core.config import settings
from app.core.securite import NOM_COOKIE_JWT, attributs_cookie_jwt
from app.db.session import get_db
from app.models.utilisateur import Utilisateur
from app.schemas.utilisateur import ConnexionEntree, InscriptionEntree, UtilisateurSortie
from app.services.authentification import connecter, inscrire

router = APIRouter()


@router.post("/inscription", response_model=UtilisateurSortie, status_code=201)
def inscription(donnees: InscriptionEntree, db: Session = Depends(get_db)) -> UtilisateurSortie:
    # L'inscription ne connecte pas l'utilisateur : ni cookie ni JWT (voir la connexion).
    return inscrire(db, donnees)


@router.post("/connexion", response_model=UtilisateurSortie, status_code=200)
def connexion(
    donnees: ConnexionEntree, response: Response, db: Session = Depends(get_db)
) -> UtilisateurSortie:
    utilisateur, jeton = connecter(db, donnees)
    # Le jeton ne voyage que dans le cookie HttpOnly, jamais dans le corps JSON.
    response.set_cookie(
        key=NOM_COOKIE_JWT,
        value=jeton,
        max_age=settings.jwt_expire_minutes * 60,
        **attributs_cookie_jwt(),
    )
    return utilisateur


@router.post("/deconnexion", status_code=204, dependencies=[Depends(utilisateur_courant)])
def deconnexion(response: Response) -> None:
    # Efface seulement le cookie : le JWT n'est pas révoqué et reste valable jusqu'à son `exp`.
    # L'en-tête est posé sur la réponse injectée ; un Response neuf le perdrait.
    response.delete_cookie(key=NOM_COOKIE_JWT, **attributs_cookie_jwt())


@router.get("/moi", response_model=UtilisateurSortie)
def moi(utilisateur: Utilisateur = Depends(utilisateur_courant)) -> Utilisateur:
    return utilisateur
