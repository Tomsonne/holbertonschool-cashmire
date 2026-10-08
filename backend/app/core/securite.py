import uuid
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

# PasswordHasher() utilise Argon2id avec les paramètres par défaut recommandés d'argon2-cffi.
_hasher = PasswordHasher()

# Nom du cookie portant le JWT (choix d'équipe, absent du contrat) : réutilisé par #9 et #10.
NOM_COOKIE_JWT = "access_token"

# Marge accordée à l'horloge lors de la lecture d'un jeton. L'`iat` d'un jeton est posé à sa création :
# si l'horloge recule ensuite de quelques fractions de seconde (resynchronisation NTP, machine
# virtuelle, deux serveurs légèrement décalés), il paraîtrait « dans le futur » et un jeton valide
# serait refusé. Sans cette marge, une 401 apparaît au hasard juste après une connexion réussie.
TOLERANCE_HORLOGE_SECONDES = 10


def attributs_cookie_jwt() -> dict[str, Any]:
    """Emplacement et sécurité du cookie JWT, communs à la connexion et à la déconnexion.

    Un navigateur n'efface un cookie que si `Path` (et le domaine) correspondent : les deux routes
    doivent donc partager ces valeurs. Fonction plutôt que constante : `Secure` dépend de
    l'environnement lu au moment de l'appel. `Max-Age` reste propre à la connexion.
    """
    return {
        "path": "/",
        "httponly": True,
        "samesite": "lax",
        "secure": settings.environment == "production",
    }


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
            leeway=TOLERANCE_HORLOGE_SECONDES,
        )
        # Converti en UUID avant toute requête SQL ; un sub qui n'en est pas un donne None.
        return uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError, TypeError, AttributeError):
        return None
