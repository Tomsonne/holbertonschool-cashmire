"""Vérification de l'origine des requêtes d'écriture (protection CSRF, en complément de SameSite=Lax).

Enregistrée comme dépendance globale de l'application (`FastAPI(dependencies=...)`) : elle
s'exécute avant les autres dépendances et avant la route, donc avant le limiteur de connexion.
Une requête refusée n'atteint jamais la route et n'incrémente aucun compteur.

Règle, pour POST, PUT, PATCH et DELETE uniquement :
- si `Origin` est présent, il doit figurer dans `ALLOWED_ORIGINS` (comparaison exacte, `null` refusé) ;
- sinon, on compare l'origine extraite de `Referer` ;
- sans aucun des deux en-têtes, la requête est refusée.
"""

from urllib.parse import urlsplit

from fastapi import Request

from app.core.config import settings
from app.core.erreurs import ErreurApi

METHODES_CONTROLEES = {"POST", "PUT", "PATCH", "DELETE"}


def _origine_du_referer(referer: str) -> str | None:
    # Un Referer illisible (ex. `http://[abc/`) est traité comme absent, donc refusé, et non en 500.
    try:
        parties = urlsplit(referer)
    except ValueError:
        return None
    if not parties.scheme or not parties.netloc:
        return None
    return f"{parties.scheme}://{parties.netloc}"


def verifier_origine(request: Request) -> None:
    if request.method not in METHODES_CONTROLEES:
        return
    origine = request.headers.get("origin")
    if origine is None:
        referer = request.headers.get("referer")
        origine = _origine_du_referer(referer) if referer else None
    # Liste lue à chaque appel : la configuration reste la seule source.
    if origine not in settings.origines_autorisees:
        raise ErreurApi(403, "Origine non autorisée.")
