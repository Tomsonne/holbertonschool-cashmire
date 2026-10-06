from collections.abc import Iterator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def obtenir_session() -> Iterator[Session]:
    """Dépendance FastAPI partagée : ouvre une session par requête et la ferme à la fin."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
