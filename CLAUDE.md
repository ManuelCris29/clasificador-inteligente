# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Fuente de verdad

`SPEC.md` define el alcance, el contrato de la API, los valores permitidos y los criterios
de aceptación. Ante cualquier duda sobre *qué* construir, leer SPEC.md antes de implementar.
Este archivo cubre solo *cómo* trabajar en el repo y las invariantes que no son obvias
leyendo el código.

Estado actual: el proyecto aún no tiene código. La primera sesión de implementación debe
crear la estructura descrita en SPEC.md §6 y completar la sección de comandos de abajo.

## Comandos

```bash
pip install -r requirements.txt          # dependencias
uvicorn app.main:app --reload            # servidor de desarrollo → http://127.0.0.1:8000/docs
pytest                                   # suite completa
pytest tests/test_clasificacion.py::test_soporte_tecnico -v   # un solo test
```

Requiere `ANTHROPIC_API_KEY` en `.env` (ver `.env.example`).

## Arquitectura

Flujo de una petición: `api/routes/solicitudes.py` valida la entrada con
`schemas/solicitud.py` → `services/solicitud_service.py` orquesta →
`services/ia_service.py` llama a Claude → la salida se valida contra el schema
`ClasificacionSolicitud` → `repositories/solicitud_repository.py` persiste →
se devuelve el modelo de respuesta.

La separación en capas existe para que el LLM quede aislado en `ia_service`: es el único
punto que conoce el SDK de Anthropic, y por tanto el único que hay que tocar para cambiar
de proveedor, añadir caché, reintentos o procesamiento asíncrono (SPEC.md §19, §29).

## Invariantes

Estas reglas son el núcleo del ejercicio; romperlas invalida el proyecto.

- **La respuesta del LLM no es confiable hasta validarla.** Nunca persistir ni devolver
  texto libre del modelo. Todo pasa por `ClasificacionSolicitud` (Pydantic) primero.
- **Vocabularios cerrados.** `categoria`, `prioridad` y `area` son Enums definidos en
  `schemas/`. El modelo no puede inventar valores; los fallbacks son `"Otro"` (categoría)
  y `"Sin asignar"` (área). Valores permitidos en SPEC.md §9–§11.
- **El prompt vive en `app/prompts/clasificador.txt`**, fuera del código de negocio, para
  poder iterarlo sin tocar la lógica.
- **Una sola llamada al LLM por solicitud.** Sin reintentos en bucle ni pasadas múltiples;
  es la restricción de costo y latencia del proyecto (SPEC.md §18–§19).
- **Errores**: entrada inválida → 400, fallo al hablar con Claude → 502, resto → 500.
  Las respuestas de error nunca exponen stack traces, prompts internos ni la API key.
- **El id del modelo de Claude se configura en `core/config.py`**, no hardcodeado en el
  servicio, para poder ajustar costo/latencia sin cambiar código.

## Context7

Antes de implementar contra FastAPI, Pydantic, SQLAlchemy o el SDK de Anthropic, consultar
Context7 para verificar la API vigente de la versión instalada. El conocimiento previo del
modelo no es fuente definitiva cuando la librería puede haber cambiado. Detalle completo y
prioridad de fuentes en SPEC.md §31.

Cuando una consulta a Context7 determine una decisión técnica relevante (p. ej. qué
mecanismo usar para forzar salida estructurada del modelo), registrarla brevemente en el
README con motivo y alternativa descartada.

## Regla de explicación del desarrollo

Durante el desarrollo, Claude debe explicar de forma resumida las operaciones importantes
para que el usuario pueda comprender qué se está haciendo y por qué.

Debe utilizar la skill `development-explainer` para definir el formato y comportamiento de
estas explicaciones.

Para operaciones importantes utilizar:

```text
[FASE]

Qué hago:
...

Por qué:
...

Resultado:
...
```

La explicación debe ser breve y enfocarse en:

- Decisiones técnicas.
- Arquitectura.
- Cambios importantes.
- Uso de Context7.
- Dependencias.
- Seguridad.
- Errores.
- Pruebas.
- Resultados.

No explicar cada línea de código ni cada comando trivial.

Las decisiones importantes deben registrarse también en:

```text
docs/process/DEVELOPMENT_LOG.md
```

Nunca afirmar que se consultó Context7, se ejecutó una prueba o se verificó una
documentación si realmente no se realizó.

El objetivo es que el usuario pueda seguir el proceso de desarrollo y entender las
decisiones técnicas sin tener que revisar todo el código.
