import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

logger = logging.getLogger("denarius.db")

connect_args = {}
db_url = settings.database_url
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

try:
    if not db_url.startswith("sqlite"):
        # Timeout corto de 2 segundos para no bloquear si postgres no está levantado
        probe_engine = create_engine(db_url, connect_args={"connect_timeout": 2} if "psycopg" in db_url else {})
        with probe_engine.connect() as conn:
            pass
        engine = probe_engine
    else:
        engine = create_engine(db_url, connect_args=connect_args)
except Exception as e:
    print(f"[DB] PostgreSQL no disponible ({e}). Usando SQLite local: sqlite:///./denarius.db")
    db_url = "sqlite:///./denarius.db"
    connect_args = {"check_same_thread": False}
    engine = create_engine(db_url, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

