"""Orquestación del caso de uso "procesar una solicitud" (SPEC §3, §15, §16).

Flujo: clasificar con IA → (la respuesta llega ya validada) → persistir →
devolver el modelo de respuesta. No conoce HTTP ni el SDK de Anthropic.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories import solicitud_repository
from app.schemas.solicitud import SolicitudCreate, SolicitudResponse
from app.services import ia_service


def procesar_solicitud(db: Session, entrada: SolicitudCreate) -> SolicitudResponse:
    """Clasifica y almacena una solicitud.

    Propaga `IAServiceError` / `RespuestaIAInvalida` sin capturarlas: si no hay
    clasificación válida no se persiste nada, y la capa HTTP decide el código de
    estado (SPEC §17).
    """
    clasificacion = ia_service.clasificar(entrada.texto)
    solicitud = solicitud_repository.guardar(db, entrada.texto, clasificacion)
    return SolicitudResponse.model_validate(solicitud)
