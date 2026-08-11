"""Configuración común de la suite de pruebas.

El entorno se fija **antes** de importar nada de `app`, para que la
configuración se construya con valores de prueba y sin `.env` real.

Las pruebas marcadas con `@pytest.mark.real_api` son la excepción: necesitan una
API key auténtica y consumen tokens, así que se saltan automáticamente salvo que
haya una key real disponible.
"""

import os

import pytest

# Se guarda la key real (si la hay) antes de sobrescribir el entorno, para que
# las pruebas `real_api` puedan usarla.
_ENV_ORIGINAL = os.environ.get("ANTHROPIC_API_KEY")

os.environ["ANTHROPIC_API_KEY"] = "test-key-no-real"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"


def _api_key_real() -> str | None:
    """Devuelve una API key auténtica de entorno o `.env`, o `None`.

    Se considera auténtica solo si tiene el prefijo real de Anthropic; el
    marcador de posición de `.env.example` no cuenta.
    """
    candidatas = [_ENV_ORIGINAL]

    ruta_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.isfile(ruta_env):
        with open(ruta_env, encoding="utf-8") as fh:
            for linea in fh:
                linea = linea.strip()
                if linea.startswith("ANTHROPIC_API_KEY="):
                    candidatas.append(linea.split("=", 1)[1].strip().strip("'\""))

    for valor in candidatas:
        if valor and valor.startswith("sk-ant-"):
            return valor
    return None


@pytest.fixture(scope="session")
def api_key_real() -> str:
    key = _api_key_real()
    if not key:
        pytest.skip(
            "Sin API key real. Escribe tu clave en `.env` "
            "(ANTHROPIC_API_KEY=sk-ant-...) para ejecutar estas pruebas."
        )
    return key
