import re
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Une origine telle que l'envoie un navigateur : schéma http(s), hôte, port optionnel. Ni chemin,
# ni `/` final, ni joker `*` : la comparaison avec l'en-tête `Origin` est exacte.
_FORMAT_ORIGINE = re.compile(r"https?://[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?(:[0-9]{1,5})?")


# Début des secrets publics du dépôt : `.env.example`, `tests/conftest.py` et la CI. Quiconque lit le
# dépôt peut fabriquer un jeton valide avec eux : ils sont refusés en production.
_DEBUTS_DE_SECRETS_PUBLICS = ("replace-with-", "cle-de-test-", "ci-only-")


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://cashmire:cashmire@localhost:5432/cashmire"
    # Toute autre valeur empêche de démarrer : une faute de frappe ne doit pas désactiver `Secure`.
    environment: Literal["development", "production"] = "development"
    # Aucune valeur par défaut : une clé absente, vide ou trop courte empêche de démarrer,
    # y compris en développement (et aussi pour `alembic`, qui importe ce module).
    jwt_secret: str = Field(min_length=32)
    # Source unique de la durée : `exp` du JWT et `max_age` du cookie.
    jwt_expire_minutes: int = Field(default=30, gt=0)
    # Origines séparées par des virgules ; lues sous forme de liste via `origines_autorisees`.
    allowed_origins: str = "http://localhost:5173"

    # hide_input_in_errors : l'erreur de validation ne recopie pas la clé fournie dans les logs.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    @field_validator("allowed_origins")
    @classmethod
    def verifier_origines(cls, valeur: str) -> str:
        # Une chaîne vide ou une virgule en trop donne une entrée vide, refusée comme les autres.
        origines = [origine.strip() for origine in valeur.split(",")]
        if not all(_FORMAT_ORIGINE.fullmatch(origine) for origine in origines):
            # Message fixe : la valeur fournie n'est pas recopiée.
            raise ValueError(
                "ALLOWED_ORIGINS doit lister des origines http(s)://hote[:port] séparées par des virgules."
            )
        return ",".join(origines)

    @model_validator(mode="after")
    def refuser_un_secret_public_en_production(self) -> "Settings":
        # La casse et les espaces en tête ne doivent pas contourner le refus.
        secret = self.jwt_secret.strip().lower()
        if self.environment == "production" and secret.startswith(_DEBUTS_DE_SECRETS_PUBLICS):
            # Message fixe : la valeur fournie n'est pas recopiée.
            raise ValueError(
                "JWT_SECRET est une valeur d'exemple publique : générez un secret aléatoire avant "
                "la production (openssl rand -hex 32), voir le README."
            )
        return self

    @property
    def origines_autorisees(self) -> list[str]:
        return self.allowed_origins.split(",")


settings = Settings()
