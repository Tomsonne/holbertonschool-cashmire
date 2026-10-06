from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

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
