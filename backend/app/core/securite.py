import uuid

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

# PasswordHasher() utilise Argon2id avec les paramètres par défaut recommandés d'argon2-cffi.
_hasher = PasswordHasher()

# Nom du cookie portant le JWT (choix d'équipe, absent du contrat) : réutilisé par #9 et #10.
NOM_COOKIE_JWT = "access_token"


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    return _hasher.hash(mot_de_passe)


def verifier_mot_de_passe(hache: str, mot_de_passe: str) -> bool:
    # Seul un mot de passe différent donne False. Un hash illisible ou une erreur du module
    # remonte (500 générique) au lieu d'être confondu avec un mauvais mot de passe.
    try:
        return _hasher.verify(hache, mot_de_passe)
    except VerifyMismatchError:
        return False


def decoder_jwt(jeton: str) -> uuid.UUID | None:
    """Renvoie l'UUID du `sub` si le jeton est valide, sinon None (sans dire pourquoi).

    Signature, expiration et présence de `exp` et `sub` sont vérifiées. L'algorithme est imposé
    ici : il n'est jamais lu dans l'en-tête du jeton.
    """
    try:
        claims = jwt.decode(
            jeton,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        # Converti en UUID avant toute requête SQL ; un sub qui n'en est pas un donne None.
        return uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError, TypeError, AttributeError):
        return None
