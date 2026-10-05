from sqlalchemy import text
from sqlalchemy.engine import Engine


def database_is_available(engine: Engine) -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
