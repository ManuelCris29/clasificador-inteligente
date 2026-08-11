"""Acceso a datos de solicitudes (SPEC §6, §16).

Aísla SQLAlchemy del resto de la aplicación: los servicios trabajan con schemas
Pydantic y no conocen sesiones ni consultas.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.solicitud import Solicitud
from app.schemas.solicitud import ClasificacionSolicitud


def guardar(
    db: Session, texto_original: str, clasificacion: ClasificacionSolicitud
) -> Solicitud:
    """Persiste una solicitud ya clasificada y validada.

    `clasificacion` es una instancia de `ClasificacionSolicitud`, de modo que a
    esta capa nunca llega texto libre del modelo (SPEC §15).
    """
    solicitud = Solicitud(
        texto_original=texto_original,
        categoria=clasificacion.categoria.value,
        prioridad=clasificacion.prioridad.value,
        area=clasificacion.area.value,
        resumen=clasificacion.resumen,
        requiere_intervencion_humana=clasificacion.requiere_intervencion_humana,
    )
    db.add(solicitud)
    db.commit()
    db.refresh(solicitud)
    return solicitud
