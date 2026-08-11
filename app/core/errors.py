"""Errores de dominio y su mapeo a códigos HTTP (SPEC §17).

Las capas internas lanzan estas excepciones; la capa HTTP las traduce a
respuestas. Ningún mensaje aquí debe contener la API key, el prompt interno ni
un stack trace: son textos pensados para devolverse al cliente tal cual.
"""


class ClasificadorError(Exception):
    """Raíz de los errores propios de la aplicación. Se mapea a 500."""

    mensaje_publico = "Ocurrió un error interno al procesar la solicitud."


class IAServiceError(ClasificadorError):
    """Fallo al obtener una clasificación utilizable de Claude. Se mapea a 502.

    Cubre tanto los fallos de comunicación con el proveedor como las respuestas
    que llegan pero no cumplen el esquema: en ambos casos el problema está aguas
    arriba de nosotros y el cliente no puede corregirlo reformulando su entrada.
    """

    mensaje_publico = "No fue posible clasificar la solicitud en este momento."


class RespuestaIAInvalida(IAServiceError):
    """El modelo respondió, pero su salida no es utilizable (SPEC §15).

    Decisión: hereda de `IAServiceError`, por lo que se mapea a **502 y no a 500**.
    Motivo: el fallo está aguas arriba de nosotros y el cliente no puede corregirlo
    reformulando su entrada; 500 comunicaría que el defecto es de esta aplicación.
    """

    mensaje_publico = "La clasificación recibida no es válida."
