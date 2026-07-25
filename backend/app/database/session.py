import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.database.base import Base


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./re_points.db")

engine_options = {}
if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_database() -> None:
    """Crea las tablas que aún no existen."""
    from backend.app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_database_session() -> Generator[Session, None, None]:
    """Entrega una sesión y garantiza su cierre."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

