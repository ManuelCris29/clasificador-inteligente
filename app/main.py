"""Aplicación FastAPI: composición y manejo de errores (SPEC §17, §22, §23).

Aquí se traduce el modelo de errores de dominio (`app/core/errors.py`) a códigos
HTTP. Es el único punto donde una excepción se convierte en respuesta, y ninguna
de esas respuestas expone stack traces, prompts internos ni la API key.

Notas de costo y latencia (SPEC §18–§19), materializadas en el código:
  - Una sola llamada al LLM por solicitud; sin reintentos en bucle.
  - El prompt es corto y sin ejemplos largos; los vocabularios se inyectan desde
    los Enums, no se repiten.
  - El texto de entrada está acotado (5–2000 caracteres) antes de llegar al LLM.
  - `max_tokens` y el id del modelo son configurables, para ajustar costo y
    latencia sin tocar código.
  - Toda la IA está aislada en `ia_service`, que es donde más adelante encajan
    caché, colas o procesamiento asíncrono sin cambiar el resto.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import solicitudes
from app.core.config import get_settings
from app.core.errors import ClasificadorError, IAServiceError
from app.database.database import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Recibe solicitudes en lenguaje natural y devuelve una clasificación "
        "estructurada y validada: categoría, prioridad, área responsable, "
        "resumen y si requiere intervención humana."
    ),
    lifespan=lifespan,
)

app.include_router(solicitudes.router)


def _error(codigo: int, mensaje: str) -> JSONResponse:
    """Cuerpo de error uniforme. Solo texto pensado para el cliente."""
    return JSONResponse(status_code=codigo, content={"detail": mensaje})


@app.exception_handler(RequestValidationError)
async def _entrada_invalida(request: Request, exc: RequestValidationError):
    """Entrada inválida → 400 (SPEC §17).

    FastAPI devolvería 422 por defecto; SPEC §17 exige 400. Se reexponen solo el
    campo y el motivo de cada fallo, nunca la excepción completa.
    """
    errores = [
        {"campo": ".".join(str(p) for p in e["loc"]), "motivo": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "La solicitud enviada no es válida.", "errores": errores},
    )


@app.exception_handler(IAServiceError)
async def _fallo_ia(request: Request, exc: IAServiceError):
    """Fallo al hablar con Claude, o respuesta suya inutilizable → 502 (SPEC §17)."""
    logger.warning("Fallo del proveedor de IA: %s", type(exc).__name__)
    return _error(status.HTTP_502_BAD_GATEWAY, exc.mensaje_publico)


@app.exception_handler(ClasificadorError)
async def _error_de_dominio(request: Request, exc: ClasificadorError):
    logger.error("Error de dominio: %s", type(exc).__name__, exc_info=exc)
    return _error(status.HTTP_500_INTERNAL_SERVER_ERROR, exc.mensaje_publico)


@app.exception_handler(Exception)
async def _error_inesperado(request: Request, exc: Exception):
    """Red de seguridad: cualquier otro fallo → 500 sin filtrar el detalle."""
    logger.exception("Error inesperado procesando %s", request.url.path)
    return _error(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        ClasificadorError.mensaje_publico,
    )


@app.get("/health", tags=["infra"], summary="Comprobación de vida del servicio")
def health() -> dict[str, str]:
    return {"status": "ok"}
