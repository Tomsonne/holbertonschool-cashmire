from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.erreurs import ErreurApi
from app.core.securite import NOM_COOKIE_JWT, decoder_jwt
from app.db.session import get_db
from app.models.utilisateur import Utilisateur


def utilisateur_courant(request: Request, db: Session = Depends(get_db)) -> Utilisateur:
    """Utilisateur authentifié par le cookie JWT ; seule source de l'identité côté serveur.

    Tous les échecs lèvent la même 401, sans indice sur la cause.
    """
    jeton = request.cookies.get(NOM_COOKIE_JWT)
    utilisateur_id = decoder_jwt(jeton) if jeton else None
    utilisateur = None
    if utilisateur_id is not None:
        # select + one_or_none, pas session.get : on interroge toujours la base, jamais la
        # mémoire de la session (un compte supprimé après l'émission du jeton doit donner 401).
        utilisateur = db.scalars(
            select(Utilisateur).where(Utilisateur.id == utilisateur_id)
        ).one_or_none()
    if utilisateur is None:
        raise ErreurApi(401, "Authentification requise.")
    return utilisateur
