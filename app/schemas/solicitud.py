"""Contratos de datos de la API y del clasificador (SPEC §7–§12).

Este módulo es el núcleo de la invariante del proyecto: los vocabularios de
`categoria`, `prioridad` y `area` son cerrados (Enums), de modo que el modelo no
puede inventar valores. La salida del LLM se valida contra
`ClasificacionSolicitud` antes de persistirse o devolverse.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Límites de tamaño del texto de entrada (SPEC §18, §20): acotan el costo de la
# llamada al LLM y evitan que un cliente envíe cargas arbitrariamente grandes.
TEXTO_MIN_LENGTH = 5
TEXTO_MAX_LENGTH = 2000


class Categoria(str, Enum):
    """SPEC §9. Fallback cuando no hay encaje claro: `OTRO`."""

    SOPORTE_TECNICO = "Soporte técnico"
    RECURSOS_HUMANOS = "Recursos humanos"
    FACTURACION = "Facturación"
    VENTAS = "Ventas"
    ADMINISTRACION = "Administración"
    OTRO = "Otro"


class Prioridad(str, Enum):
    """SPEC §10. La prioridad se deduce del impacto, no de la palabra "urgente"."""

    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class AreaResponsable(str, Enum):
    """SPEC §11. Fallback cuando no se puede determinar: `SIN_ASIGNAR`."""

    TI = "TI"
    RECURSOS_HUMANOS = "Recursos Humanos"
    FINANZAS = "Finanzas"
    VENTAS = "Ventas"
    ADMINISTRACION = "Administración"
    SERVICIO_AL_CLIENTE = "Servicio al cliente"
    SIN_ASIGNAR = "Sin asignar"


class SolicitudCreate(BaseModel):
    """Entrada del endpoint `POST /solicitudes` (SPEC §7).

    Rechaza texto vacío o compuesto solo de espacios, y acota su longitud.
    """

    texto: str = Field(
        ...,
        min_length=TEXTO_MIN_LENGTH,
        max_length=TEXTO_MAX_LENGTH,
        description="Solicitud del usuario, en lenguaje natural.",
        examples=["No puedo ingresar al sistema desde esta mañana"],
    )

    @field_validator("texto")
    @classmethod
    def texto_no_vacio(cls, valor: str) -> str:
        limpio = valor.strip()
        if len(limpio) < TEXTO_MIN_LENGTH:
            raise ValueError("El texto de la solicitud no puede estar vacío.")
        return limpio


class ClasificacionSolicitud(BaseModel):
    """Salida estructurada que debe producir el modelo (SPEC §12).

    Este schema se envía a Claude como JSON Schema y se usa además para validar
    la respuesta recibida. Nada del modelo se persiste sin pasar por aquí.
    """

    model_config = ConfigDict(extra="forbid")

    categoria: Categoria = Field(description="Categoría de la solicitud.")
    prioridad: Prioridad = Field(description="Prioridad según el impacto real.")
    area: AreaResponsable = Field(description="Área responsable de atenderla.")
    resumen: str = Field(
        min_length=1,
        max_length=300,
        description="Resumen breve de la solicitud, en una frase.",
    )
    requiere_intervencion_humana: bool = Field(
        description="True si la solicitud no puede resolverse automáticamente."
    )


class SolicitudResponse(ClasificacionSolicitud):
    """Respuesta del endpoint (SPEC §8, §22): la clasificación más el id.

    `fecha_creacion` se persiste (SPEC §16) pero no forma parte del contrato de
    respuesta definido en SPEC §22; no se expone aquí.
    """

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
