"""Pruebas del endpoint `POST /solicitudes` (SPEC §17, §21, §22, §23).

El LLM se sustituye por un doble en todas las pruebas: lo que se verifica es el
contrato HTTP, el manejo de errores y que nada se persista cuando la IA falla.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.errors import IAServiceError, RespuestaIAInvalida
from app.database.database import get_engine, init_db
from app.main import app
from app.models.solicitud import Solicitud
from app.schemas.solicitud import (
    TEXTO_MAX_LENGTH,
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


@pytest.fixture
def client():
    init_db()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def ia(monkeypatch):
    """Sustituye `ia_service.clasificar`; acepta un valor o una excepción."""

    def _instalar(resultado):
        def _falso(_texto: str):
            if isinstance(resultado, Exception):
                raise resultado
            return resultado

        monkeypatch.setattr(ia_service, "clasificar", _falso)

    return _instalar


def _contar_solicitudes() -> int:
    from sqlalchemy import func, select
    from sqlalchemy.orm import Session

    with Session(get_engine()) as db:
        return db.scalar(select(func.count()).select_from(Solicitud)) or 0


# --- Camino feliz (SPEC §21 caso 1, §22) ---------------------------------------


def test_crear_solicitud_devuelve_la_clasificacion(client, ia):
    ia(CLASIFICACION_VALIDA)

    r = client.post(
        "/solicitudes", json={"texto": "No puedo ingresar al sistema desde esta mañana"}
    )

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["categoria"] == "Soporte técnico"
    assert cuerpo["area"] == "TI"
    assert isinstance(cuerpo["id"], int)
    # El contrato de SPEC §22 tiene exactamente estos campos.
    assert set(cuerpo) == {
        "id",
        "categoria",
        "prioridad",
        "area",
        "resumen",
        "requiere_intervencion_humana",
    }


def test_la_solicitud_queda_persistida(client, ia):
    ia(CLASIFICACION_VALIDA)
    antes = _contar_solicitudes()

    r = client.post("/solicitudes", json={"texto": "No puedo ingresar al sistema"})

    assert _contar_solicitudes() == antes + 1
    from sqlalchemy.orm import Session

    with Session(get_engine()) as db:
        fila = db.get(Solicitud, r.json()["id"])
    assert fila.texto_original == "No puedo ingresar al sistema"
    assert fila.fecha_creacion is not None


# --- Entrada inválida → 400 (SPEC §17, §21 caso 5) -----------------------------


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"texto": ""}, id="texto-vacio"),
        pytest.param({"texto": "     "}, id="solo-espacios"),
        pytest.param({}, id="campo-ausente"),
        pytest.param({"texto": 123}, id="tipo-incorrecto"),
        pytest.param({"texto": "x" * (TEXTO_MAX_LENGTH + 1)}, id="demasiado-largo"),
    ],
)
def test_entrada_invalida_devuelve_400(client, ia, payload):
    ia(CLASIFICACION_VALIDA)

    r = client.post("/solicitudes", json=payload)

    assert r.status_code == 400, "SPEC §17 exige 400, no el 422 por defecto de FastAPI"
    assert "errores" in r.json()


def test_entrada_invalida_no_llama_al_llm(client, monkeypatch):
    """La validación ocurre antes: una entrada mala no debe costar tokens."""
    llamadas = []
    monkeypatch.setattr(
        ia_service, "clasificar", lambda t: llamadas.append(t) or CLASIFICACION_VALIDA
    )

    client.post("/solicitudes", json={"texto": ""})

    assert llamadas == []


# --- Fallos del proveedor → 502 (SPEC §17) -------------------------------------


@pytest.mark.parametrize(
    "error", [IAServiceError(), RespuestaIAInvalida()], ids=["comunicacion", "invalida"]
)
def test_fallo_de_ia_devuelve_502(client, ia, error):
    ia(error)

    r = client.post("/solicitudes", json={"texto": "No puedo ingresar al sistema"})

    assert r.status_code == 502


def test_fallo_de_ia_no_persiste_nada(client, ia):
    ia(IAServiceError())
    antes = _contar_solicitudes()

    client.post("/solicitudes", json={"texto": "No puedo ingresar al sistema"})

    assert _contar_solicitudes() == antes


# --- Error inesperado → 500 (SPEC §17) -----------------------------------------


def test_error_inesperado_devuelve_500_sin_filtrar_detalles(client, ia):
    ia(RuntimeError("detalle interno con sk-ant-secreto"))

    r = client.post("/solicitudes", json={"texto": "No puedo ingresar al sistema"})

    assert r.status_code == 500
    cuerpo = r.text.lower()
    for filtracion in ("sk-ant", "traceback", "runtimeerror", "detalle interno"):
        assert filtracion not in cuerpo


# --- Documentación (SPEC §23) --------------------------------------------------


def test_documentacion_disponible(client):
    assert client.get("/docs").status_code == 200

    esquema = client.get("/openapi.json")
    assert esquema.status_code == 200
    assert "/solicitudes" in esquema.json()["paths"]


def test_openapi_documenta_los_vocabularios_cerrados(client):
    """El consumidor debe poder ver los valores permitidos desde la propia API."""
    defs = client.get("/openapi.json").json()["components"]["schemas"]

    assert set(defs["Categoria"]["enum"]) == {c.value for c in Categoria}
    assert set(defs["Prioridad"]["enum"]) == {p.value for p in Prioridad}
    assert set(defs["AreaResponsable"]["enum"]) == {a.value for a in AreaResponsable}
