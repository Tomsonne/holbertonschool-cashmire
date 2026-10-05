from pydantic import BaseModel


class DetailErreur(BaseModel):
    code: str
    message: str
    champs: dict[str, str] | None = None


class ReponseErreur(BaseModel):
    """Format unique de toutes les erreurs de l'API : {"erreur": {code, message, champs?}}."""

    erreur: DetailErreur
