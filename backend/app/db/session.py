from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import settings

# hide_parameters : une erreur SQL n'embarque pas les valeurs liées (email, hash) dans son texte.
engine = create_engine(settings.database_url, pool_pre_ping=True, hide_parameters=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Une session par requête, toujours fermée à la fin."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
