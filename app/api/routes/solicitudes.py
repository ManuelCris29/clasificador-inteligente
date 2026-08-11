"""Endpoint `POST /solicitudes` (SPEC §7, §8, §22).

Esta capa solo hace HTTP: valida la entrada con Pydantic, delega en el servicio
y devuelve el modelo de respuesta. No conoce Claude ni SQLAlchemy.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.schemas.solicitud import SolicitudCreate, SolicitudResponse
from app.services import solicitud_service

router = APIRouter(prefix="/solicitudes", tags=["solicitudes"])


@router.post(
    "",
    response_model=SolicitudResponse,
    # 200 y no 201: SPEC §22 define el contrato de respuesta sin fijar código, y
    # se prioriza la literalidad respecto al SPEC sobre la convención REST.
    status_code=status.HTTP_200_OK,
    summary="Clasificar y registrar una solicitud",
    response_description="La solicitud clasificada y almacenada.",
    responses={
        400: {"description": "El texto de la solicitud no es válido."},
        502: {"description": "No fue posible obtener una clasificación válida."},
        500: {"description": "Error interno."},
    },
)
def crear_solicitud(
    entrada: SolicitudCreate,
    db: Session = Depends(get_db),
) -> SolicitudResponse:
    """Analiza una solicitud en lenguaje natural y devuelve su clasificación.

    Realiza **una sola** llamada al modelo de IA (SPEC §18–§19). Si esa llamada
    falla o devuelve algo inutilizable, no se persiste nada y la respuesta es un
    502; los errores se traducen en `app/main.py`.
    """
    return solicitud_service.procesar_solicitud(db, entrada)
