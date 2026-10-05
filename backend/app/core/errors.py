from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    champs = {}
    for erreur in exc.errors():
        chemin = ".".join(str(part) for part in erreur["loc"] if part != "body") or "requete"
        champs[chemin] = str(erreur["msg"]).removeprefix("Value error, ")
    return JSONResponse(
        status_code=422,
        content={"erreur": {"code": "donnees_invalides", "message": "Les données fournies sont invalides.", "champs": champs}},
    )


async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    erreurs = {
        400: ("requete_invalide", "La requête est invalide."),
        401: ("non_authentifie", "Authentification requise."),
        404: ("introuvable", "La ressource demandée est introuvable."),
        409: ("conflit", "La requête entre en conflit avec une ressource existante."),
        422: ("donnees_invalides", "Les données fournies sont invalides."),
        429: ("trop_de_tentatives", "Trop de tentatives. Réessayez plus tard."),
    }
    code, message = erreurs.get(exc.status_code, ("erreur_interne", "Une erreur interne est survenue."))
    return JSONResponse(
        status_code=exc.status_code,
        content={"erreur": {"code": code, "message": message}},
        headers=exc.headers,
    )


def erreur_api(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"erreur": {"code": code, "message": message}})
