from argon2 import PasswordHasher

# PasswordHasher() utilise Argon2id avec les paramètres par défaut recommandés d'argon2-cffi.
_hasher = PasswordHasher()


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    return _hasher.hash(mot_de_passe)
