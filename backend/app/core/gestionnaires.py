"""Gestionnaires d'erreurs : toutes les erreurs de l'API sortent au même format.

Aucune réponse ne contient de trace, de détail SQL, ni la valeur envoyée par le client
(un mot de passe mal saisi ne doit jamais revenir dans une erreur de validation).
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.erreurs import CODE_PAR_DEFAUT, CODES_PAR_STATUT, ErreurApi
from app.schemas.erreur import DetailErreur, ReponseErreur

journal = logging.getLogger("cashmire.erreurs")

# Messages français par type d'erreur Pydantic. Les types inconnus donnent "Valeur invalide."
MESSAGES_VALIDATION = {
    "missing": "Champ obligatoire.",
    "string_too_short": "Valeur trop courte.",
    "string_too_long": "Valeur trop longue.",
    "greater_than": "Valeur trop petite.",
    "greater_than_equal": "Valeur trop petite.",
    "less_than": "Valeur trop grande.",
    "less_than_equal": "Valeur trop grande.",
    "decimal_max_places": "Deux décimales maximum.",
}
MESSAGE_VALEUR_INVALIDE = "Valeur invalide."
MESSAGE_FORMAT_INVALIDE = "Format invalide."

# Message par statut pour les erreurs HTTP levées par FastAPI/Starlette (404 de route, 405...).
MESSAGES_HTTP = {
    401: "Authentification requise.",
    404: "Ressource introuvable.",
    405: "Méthode non autorisée.",
}
MESSAGE_HTTP_PAR_DEFAUT = "Requête invalide."

# Premier élément de `loc` qui indique d'où vient la valeur, pas un nom de champ.
ORIGINES = {"body", "query", "path", "header", "cookie"}


def reponse_erreur(
    statut: int,
    code: str,
    message: str,
    champs: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    corps = ReponseErreur(erreur=DetailErreur(code=code, message=message, champs=champs))
    return JSONResponse(
        status_code=statut,
        content=corps.model_dump(exclude_none=True),
        headers=headers,
    )


def _nom_du_champ(localisation: tuple) -> str:
    elements = [str(e) for e in localisation if e not in ORIGINES]
    return ".".join(elements) if elements else "corps"


def _message_validation(type_erreur: str) -> str:
    if type_erreur in MESSAGES_VALIDATION:
        return MESSAGES_VALIDATION[type_erreur]
    if type_erreur.endswith(("_parsing", "_type")):
        return MESSAGE_FORMAT_INVALIDE
    return MESSAGE_VALEUR_INVALIDE


async def gerer_erreur_api(_requete: Request, erreur: ErreurApi) -> JSONResponse:
    return reponse_erreur(erreur.statut, erreur.code, erreur.message, erreur.champs)


async def gerer_erreur_validation(
    _requete: Request, erreur: RequestValidationError
) -> JSONResponse:
    details = erreur.errors()
    # Corps JSON mal formé : requête invalide (400), pas une donnée invalide (422).
    if any(d["type"] == "json_invalid" for d in details):
        return reponse_erreur(400, CODES_PAR_STATUT[400], "Le corps de la requête n'est pas un JSON valide.")
    champs: dict[str, str] = {}
    for detail in details:
        # On ne garde que le premier message par champ ; "input" n'est jamais renvoyé.
        champs.setdefault(_nom_du_champ(detail["loc"]), _message_validation(detail["type"]))
    return reponse_erreur(
        422, CODES_PAR_STATUT[422], "Certaines données sont invalides.", champs
    )


async def gerer_erreur_http(_requete: Request, erreur: StarletteHTTPException) -> JSONResponse:
    code = CODES_PAR_STATUT.get(erreur.status_code, CODE_PAR_DEFAUT)
    message = MESSAGES_HTTP.get(erreur.status_code, MESSAGE_HTTP_PAR_DEFAUT)
    return reponse_erreur(erreur.status_code, code, message, headers=erreur.headers)


async def gerer_erreur_inattendue(_requete: Request, erreur: Exception) -> JSONResponse:
    # La trace reste dans les journaux du serveur, jamais dans la réponse.
    journal.error("Erreur inattendue", exc_info=erreur)
    return reponse_erreur(500, CODES_PAR_STATUT[500], "Une erreur interne est survenue.")


def installer_gestionnaires(app: FastAPI) -> None:
    app.add_exception_handler(ErreurApi, gerer_erreur_api)
    app.add_exception_handler(RequestValidationError, gerer_erreur_validation)
    app.add_exception_handler(StarletteHTTPException, gerer_erreur_http)
    app.add_exception_handler(Exception, gerer_erreur_inattendue)
