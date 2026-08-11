"""Pruebas del servicio de IA (SPEC §14, §15, §17).

Ninguna prueba llama a Claude: la respuesta del SDK se sustituye por dobles.
Lo que se verifica es el contrato del prompt y el manejo de las respuestas que
*no* sirven, que es donde está el riesgo real.
"""

from __future__ import annotations

import httpx
import pytest

from app.core.errors import IAServiceError, RespuestaIAInvalida
from app.schemas.solicitud import (
    AreaResponsable,
    Categoria,
    ClasificacionSolicitud,
    Prioridad,
)
from app.services import ia_service

CLASIFICACION_VALIDA = ClasificacionSolicitud(
    categoria=Categoria.SOPORTE_TECNICO,
    prioridad=Prioridad.ALTA,
    area=AreaResponsable.TI,
    resumen="Usuario no puede acceder al sistema",
    requiere_intervencion_humana=True,
)


class RespuestaFalsa:
    """Doble mínimo de `ParsedMessage`: solo lo que `clasificar` consulta."""

    def __init__(self, parsed_output=None, stop_reason="end_turn"):
        self.parsed_output = parsed_output
        self.stop_reason = stop_reason


class ClienteFalso:
    def __init__(self, resultado):
        self._resultado = resultado
        self.llamadas = 0

    @property
    def messages(self):
        return self

    def parse(self, **_kwargs):
        self.llamadas += 1
        if isinstance(self._resultado, Exception):
            raise self._resultado
        return self._resultado


@pytest.fixture
def cliente_falso(monkeypatch):
    """Sustituye el cliente de Anthropic; devuelve el doble para inspeccionarlo."""

    def _instalar(resultado):
        cliente = ClienteFalso(resultado)
        monkeypatch.setattr(ia_service, "_cliente", lambda: cliente)
        return cliente

    return _instalar


# --- Prompt (SPEC §14) ---------------------------------------------------------


def test_prompt_incluye_todos_los_valores_permitidos():
    """El prompt debe listar los tres vocabularios completos, sin excepción.

    Es la prueba que impide que el prompt y los Enums se desincronicen.
    """
    prompt = ia_service.construir_prompt("No puedo ingresar al sistema")

    for enum_cls in (Categoria, Prioridad, AreaResponsable):
        for miembro in enum_cls:
            assert miembro.value in prompt, f"falta '{miembro.value}' en el prompt"


def test_prompt_incluye_el_texto_y_no_deja_marcadores():
    prompt = ia_service.construir_prompt("Me cobraron dos veces la misma factura")

    assert "Me cobraron dos veces la misma factura" in prompt
    for marcador in ("{categorias}", "{prioridades}", "{areas}", "{texto}"):
        assert marcador not in prompt


def test_prompt_tolera_llaves_literales_en_la_plantilla(monkeypatch):
    """El `.txt` se edita a mano; una llave literal no debe romper la construcción."""
    monkeypatch.setattr(
        ia_service, "_plantilla_prompt", lambda: 'Ejemplo: {"a": 1}\n{texto}'
    )

    assert ia_service.construir_prompt("hola") == 'Ejemplo: {"a": 1}\nhola'


# --- Camino feliz --------------------------------------------------------------


def test_clasificar_devuelve_la_clasificacion_validada(cliente_falso):
    cliente = cliente_falso(RespuestaFalsa(parsed_output=CLASIFICACION_VALIDA))

    resultado = ia_service.clasificar("No puedo ingresar al sistema")

    assert resultado == CLASIFICACION_VALIDA
    assert cliente.llamadas == 1, "SPEC §18: una sola llamada al LLM por solicitud"


# --- Respuestas inutilizables (SPEC §15, §17) ----------------------------------


def test_clasificar_falla_si_no_hay_salida_estructurada(cliente_falso):
    """`parsed_output` es Optional en el SDK; None debe dar 502, no AttributeError."""
    cliente_falso(RespuestaFalsa(parsed_output=None))

    with pytest.raises(RespuestaIAInvalida):
        ia_service.clasificar("No puedo ingresar al sistema")


def test_clasificar_falla_si_el_modelo_rechaza(cliente_falso):
    cliente_falso(RespuestaFalsa(parsed_output=None, stop_reason="refusal"))

    with pytest.raises(RespuestaIAInvalida):
        ia_service.clasificar("texto cualquiera")


def test_respuesta_invalida_se_trata_como_fallo_del_proveedor():
    """Decisión registrada: `RespuestaIAInvalida` mapea a 502, no a 500."""
    assert issubclass(RespuestaIAInvalida, IAServiceError)


# --- Fallo de comunicación (SPEC §17) ------------------------------------------


def test_error_del_sdk_se_traduce_a_error_de_servicio(cliente_falso):
    import anthropic

    fallo = anthropic.APIConnectionError(request=httpx.Request("POST", "https://x"))
    cliente_falso(fallo)

    with pytest.raises(IAServiceError):
        ia_service.clasificar("No puedo ingresar al sistema")


def test_el_error_publico_no_filtra_detalles_internos():
    """SPEC §17, §20: nada de API keys, prompts ni stack traces hacia el cliente."""
    for error in (IAServiceError(), RespuestaIAInvalida()):
        mensaje = error.mensaje_publico.lower()
        for filtracion in ("api", "key", "traceback", "anthropic", "prompt"):
            assert filtracion not in mensaje
