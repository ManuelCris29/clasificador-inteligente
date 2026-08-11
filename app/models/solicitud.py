"""Modelo ORM de una solicitud procesada (SPEC §16)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


class Solicitud(Base):
    __tablename__ = "solicitudes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    texto_original: Mapped[str] = mapped_column(Text, nullable=False)

    # Los valores de categoría/prioridad/área se guardan como texto ya validado
    # contra los Enums de `schemas/`. Se evita el tipo Enum del motor para no
    # tener que migrar la tabla cada vez que se añade un valor al vocabulario.
    categoria: Mapped[str] = mapped_column(String(50), nullable=False)
    prioridad: Mapped[str] = mapped_column(String(20), nullable=False)
    area: Mapped[str] = mapped_column(String(50), nullable=False)

    resumen: Mapped[str] = mapped_column(String(300), nullable=False)
    requiere_intervencion_humana: Mapped[bool] = mapped_column(Boolean, nullable=False)

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
