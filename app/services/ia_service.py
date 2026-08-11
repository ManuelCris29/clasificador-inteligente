"""Única puerta de salida hacia Claude (SPEC §13–§15).

Este es el único módulo que conoce el SDK de Anthropic. Cambiar de proveedor,
añadir caché, reintentos o procesamiento asíncrono se hace aquí y en ningún otro
sitio.

Restricción del proyecto (SPEC §18–§19): **una sola llamada al LLM por
solicitud**. Sin bucles de reintento ni pasadas múltiples.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import anthropic

from app.core.config import get_settings
from app.core.errors import IAServiceError, RespuestaIAInvalida
from app.schemas.solicitud import (
    AreaResponsable,
    Categoria,
    ClasificacionSolicitud,
    Prioridad,
)

logger = logging.getLogger(__name__)

_RUTA_PROMPT = Path(__file__).resolve().parent.parent / "prompts" / "clasificador.txt"


@lru_cache
def _plantilla_prompt() -> str:
    """Lee el prompt de disco una sola vez (SPEC §14: vive fuera del código)."""
    return _RUTA_PROMPT.read_text(encoding="utf-8")


def _listar(enum_cls: type) -> str:
    return "\n".join(f"- {miembro.value}" for miembro in enum_cls)


def construir_prompt(texto: str) -> str:
    """Rellena la plantilla con los vocabularios y el texto de la solicitud.

    Los valores permitidos se inyectan desde los Enums en lugar de repetirse en
    el `.txt`: así el prompt y la validación nunca pueden desincronizarse.

    Se sustituye con `str.replace` y no con `str.format`: el `.txt` está pensado
    para editarse a mano, y `format` fallaría con un `KeyError` en cuanto alguien
    escribiera una llave literal (por ejemplo un ejemplo de JSON) en el prompt.
    """
    sustituciones = {
        "{categorias}": _listar(Categoria),
        "{prioridades}": _listar(Prioridad),
        "{areas}": _listar(AreaResponsable),
        "{texto}": texto,
    }
    prompt = _plantilla_prompt()
    for marcador, valor in sustituciones.items():
        prompt = prompt.replace(marcador, valor)
    return prompt


@lru_cache
def _cliente() -> anthropic.Anthropic:
    """Cliente de Anthropic. La API key llega por variable de entorno (SPEC §13)."""
    return anthropic.Anthropic(api_key=get_settings().anthropic_api_key)


def clasificar(texto: str) -> ClasificacionSolicitud:
    """Clasifica `texto` con Claude y devuelve el resultado **ya validado**.

    Usa Structured Outputs: el JSON Schema de `ClasificacionSolicitud` se envía
    en la petición y el SDK valida la respuesta contra él. Aun así tratamos el
    resultado como no confiable hasta comprobarlo (SPEC §15).

    Raises:
        IAServiceError: fallo de comunicación con el proveedor.
        RespuestaIAInvalida: el modelo respondió algo que no cumple el esquema.
    """
    settings = get_settings()

    try:
        respuesta = _cliente().messages.parse(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            messages=[{"role": "user", "content": construir_prompt(texto)}],
            output_format=ClasificacionSolicitud,
        )
    except anthropic.APIError as exc:
        # No propagamos `exc` hacia el cliente: puede contener detalles internos.
        # Sí registramos el status y el `request_id` de Anthropic, que es lo que
        # permite distinguir un problema de red de uno de cuota o de credenciales
        # (y lo que pide su soporte). No están en todas las excepciones: los
        # errores de conexión no llegan a tener respuesta HTTP.
        logger.error(
            "Fallo al llamar a Claude: %s (status=%s, request_id=%s)",
            type(exc).__name__,
            getattr(exc, "status_code", "n/d"),
            getattr(exc, "request_id", "n/d"),
            exc_info=exc,
        )
        raise IAServiceError from exc

    if respuesta.stop_reason == "refusal":
        logger.warning("Claude rechazó clasificar la solicitud.")
        raise RespuestaIAInvalida

    clasificacion = respuesta.parsed_output
    if clasificacion is None:
        logger.error("Claude no devolvió una salida estructurada utilizable.")
        raise RespuestaIAInvalida

    return clasificacion
