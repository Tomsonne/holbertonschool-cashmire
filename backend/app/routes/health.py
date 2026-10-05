from fastapi import APIRouter, Response
from app.db.session import engine
from app.schemas.health import HealthResponse
from app.services.health import database_is_available

router = APIRouter()


@router.get("/health", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
def health(response: Response) -> HealthResponse:
    if database_is_available(engine):
        return HealthResponse(statut="ok", base_de_donnees="disponible")
    response.status_code = 503
    return HealthResponse(statut="degrade", base_de_donnees="indisponible")
