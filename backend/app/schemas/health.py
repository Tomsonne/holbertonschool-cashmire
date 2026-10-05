from typing import Literal
from pydantic import BaseModel


class HealthResponse(BaseModel):
    statut: Literal["ok", "degrade"]
    base_de_donnees: Literal["disponible", "indisponible"]
