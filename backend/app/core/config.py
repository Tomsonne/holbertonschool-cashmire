from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://cashmire:cashmire@localhost:5432/cashmire"
    environment: str = "development"
    dev_user_email: str = "cashmire-dev@example.invalid"
    jwt_secret: str = ""
    jwt_expire_minutes: int = 30
    allowed_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
