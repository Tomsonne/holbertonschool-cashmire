"""Limitation des tentatives de connexion : 5 échecs sur 15 minutes par email.

La clé est l'email normalisé (pas l'IP). Les emails inconnus comptent comme les autres, pour
que le 429 ne révèle pas l'existence d'un compte. Seuls les échecs sont comptés, et le compteur
est remis à zéro après une connexion réussie.

Limites connues (MVP) :
- le compteur est en mémoire : chaque worker uvicorn a le sien et un redémarrage l'efface ;
- un attaquant qui connaît un email peut bloquer temporairement la connexion de ce compte ;
- deux requêtes simultanées sur un même email peuvent passer avant l'enregistrement d'un échec ;
- la mémoire n'a pas de borne dure (voir SEUIL_PURGE).
"""

import threading
import time

from app.core.erreurs import ErreurApi

MAX_ECHECS = 5
FENETRE_SECONDES = 15 * 60
# Au-delà, on purge les clés expirées à chaque nouvel échec. Pas de borne dure : le MVP accepte ce risque.
SEUIL_PURGE = 10_000

_echecs: dict[str, list[float]] = {}
# Les routes synchrones s'exécutent dans un pool de threads.
_verrou = threading.Lock()


def _recents(email: str, maintenant: float) -> list[float]:
    limite = maintenant - FENETRE_SECONDES
    recents = [t for t in _echecs.get(email, []) if t > limite]
    if recents:
        _echecs[email] = recents
    else:
        _echecs.pop(email, None)
    return recents


def verifier_autorise(email: str) -> None:
    """Lève 429 si l'email a déjà MAX_ECHECS échecs dans la fenêtre. À appeler avant Argon2."""
    with _verrou:
        if len(_recents(email, time.monotonic())) >= MAX_ECHECS:
            raise ErreurApi(429, "Trop de tentatives, réessayez plus tard.")


def enregistrer_echec(email: str) -> None:
    with _verrou:
        maintenant = time.monotonic()
        if len(_echecs) >= SEUIL_PURGE:
            for cle in list(_echecs):
                _recents(cle, maintenant)
        _recents(email, maintenant)
        _echecs.setdefault(email, []).append(maintenant)


def reinitialiser(email: str) -> None:
    with _verrou:
        _echecs.pop(email, None)


def reinitialiser_tout() -> None:
    """Vide tous les compteurs (utilisé par les tests)."""
    with _verrou:
        _echecs.clear()
