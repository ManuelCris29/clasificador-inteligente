"""Conexión a la base de datos (SPEC §5, §16).

SQLite por ahora. La URL viene de configuración, así que migrar a MySQL más
adelante es cambiar `DATABASE_URL` y el driver, sin tocar repositorios ni
servicios.

El engine se crea de forma perezosa: importar este módulo no debe exigir que la
configuración esté completa, para que los tests puedan importar los modelos sin
un `.env` válido.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base declarativa de los modelos ORM."""


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    kwargs: dict = {}

    if url.startswith("sqlite"):
        # `check_same_thread=False`: FastAPI atiende peticiones en distintos
        # hilos y el driver de SQLite lo prohíbe por defecto.
        kwargs["connect_args"] = {"check_same_thread": False}

        if ":memory:" in url:
            # Una base en memoria vive dentro de su conexión: con el pool normal,
            # cada hilo abriría una base vacía distinta. `StaticPool` fuerza una
            # única conexión compartida. Solo aplica a este caso (tests).
            kwargs["poolclass"] = StaticPool

    return create_engine(url, **kwargs)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión por petición, siempre cerrada."""
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Crea las tablas si no existen.

    Suficiente para este proyecto; un sistema en producción usaría migraciones
    (Alembic) en lugar de `create_all`.
    """
    from app.models import solicitud as _modelo  # noqa: F401  (registra la tabla)

    Base.metadata.create_all(bind=get_engine())
