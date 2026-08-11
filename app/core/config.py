"""Configuración de la aplicación (SPEC §13, §18, §20, §24).

Toda la configuración se lee de variables de entorno / `.env`. En particular la
API key de Anthropic y el id del modelo de Claude nunca están hardcodeados en
la lógica de negocio: cambiar de modelo (costo/latencia) es cambiar una variable.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Secretos / infraestructura ---
    anthropic_api_key: str
    database_url: str = "sqlite:///./solicitudes.db"

    # --- Modelo de IA (SPEC §18: el modelo es un parámetro, no una constante) ---
    #
    # Política de selección de modelo:
    #   claude-sonnet-5  → POR DEFECTO. Clasificar una solicitud corta contra un
    #                      vocabulario cerrado no es una tarea difícil, y Sonnet
    #                      la resuelve con buena relación calidad/costo/latencia.
    #   claude-opus-5    → reservado para tareas complejas: razonamiento de
    #                      varios pasos, criterios ambiguos o textos largos. Hoy
    #                      este servicio no tiene ninguna, así que no se usa.
    #   claude-haiku-4-5 → opción barata para ejecutar las pruebas en bucle.
    #
    # Escalar o abaratar es cambiar `CLAUDE_MODEL` en el entorno; no hay ninguna
    # decisión de modelo incrustada en `ia_service`. Deliberadamente NO existe un
    # segundo campo "modelo para tareas complejas": sería configuración que nadie
    # lee mientras el servicio siga teniendo un único caso de uso (SPEC §4.1).
    claude_model: str = "claude-sonnet-5"
    claude_max_tokens: int = 1024

    # Nota: los límites de tamaño del texto (SPEC §20) viven en
    # `app/schemas/solicitud.py`, junto a la validación que los aplica, para no
    # tener dos fuentes de verdad.

    # --- Metadatos de la API ---
    app_name: str = "Clasificador Inteligente de Solicitudes"
    app_version: str = "1.0.0"


@lru_cache
def get_settings() -> Settings:
    """Instancia única de configuración; cacheada para no releer el `.env`."""
    return Settings()
