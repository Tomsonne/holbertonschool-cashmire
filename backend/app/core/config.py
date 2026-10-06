from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://cashmire:cashmire@localhost:5432/cashmire"
    environment: str = "development"
    dev_user_email: str = "cashmire-dev@example.invalid"
    # Aucune valeur par défaut : une clé absente, vide ou trop courte empêche de démarrer,
    # y compris en développement (et aussi pour `alembic`, qui importe ce module).
    jwt_secret: str = Field(min_length=32)
    # Source unique de la durée : `exp` du JWT et `max_age` du cookie.
    jwt_expire_minutes: int = Field(default=30, gt=0)
    allowed_origins: str = "http://localhost:5173"

    # hide_input_in_errors : l'erreur de validation ne recopie pas la clé fournie dans les logs.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)


settings = Settings()