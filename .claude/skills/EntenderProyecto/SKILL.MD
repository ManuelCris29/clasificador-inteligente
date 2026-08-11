---
name: EntenderProyecto
description: Enseña cómo se construyó el Clasificador Inteligente de Solicitudes, en el orden real en que se creó cada archivo, explicando cada clase, función y decisión técnica, y cómo probar la API con Postman. Úsala cuando el usuario pregunte cómo funciona el proyecto, por qué existe un archivo, qué hace una clase, en qué orden se construyó, cómo probarlo, o quiera aprender a levantar un proyecto así por su cuenta sin ayuda de IA.
---

# Entender el Clasificador Inteligente

Esta skill enseña el proyecto **para que el usuario sepa reconstruirlo solo**. No
es documentación de referencia: es una explicación en el orden en que se tomaron
las decisiones, con el porqué de cada una.

## Cómo usar esta skill

Lee **solo el fichero de referencia que responda a la pregunta**. Están en
`references/` y cada uno se explica por sí mismo.

| Si el usuario pregunta… | Lee |
|---|---|
| "¿Por qué FastAPI / Pydantic / un Enum?", "¿por qué no lo hago con `if`?" | `references/01-por-que-cada-pieza.md` |
| "¿Qué archivo se creó primero?", "¿cómo lo construyo yo?", "¿qué hace este archivo?" | `references/02-construccion-paso-a-paso.md` |
| "¿Qué es `BaseModel`?", "¿qué hace `lru_cache`?", "¿qué clases se usan?" | `references/03-clases-y-funciones.md` |
| "¿Cómo lo pruebo?", "¿cómo hago un POST en Postman?" | `references/04-probar-con-postman.md` |
| "Quiero hacerlo yo desde cero" | `references/05-reconstruyelo-tu.md` |

Si la pregunta abarca varios, lee solo los necesarios — no cargues los cinco.

## Reglas al enseñar

1. **Explica el problema antes que la solución.** "Se usa un Enum" no enseña
   nada; "sin un Enum, el modelo podría devolver `Facturacion` sin tilde y
   acabaría en la base de datos" sí.
2. **Cita el archivo y la línea reales** (`app/schemas/solicitud.py:28`). El
   usuario debe poder abrirlo y verlo.
3. **Cuando algo pueda comprobarse, propón el comando** que lo comprueba en vez
   de pedir que confíe.
4. **Distingue lo obligatorio de lo opcional.** Qué exige el SPEC, qué fue
   criterio de quien lo escribió y qué podría hacerse de otra forma.
5. **No inventes.** Si algo no está en las referencias ni en el código, dilo y
   ofrece leer el archivo.

## La idea central del proyecto, en un párrafo

Un modelo de lenguaje devuelve **texto**, y el texto no es confiable: puede traer
una categoría inventada, una tilde de menos o un JSON mal formado. Todo el
proyecto existe para convertir ese texto en un **dato validado** antes de que
toque la base de datos o al usuario. Esa conversión ocurre en un único sitio
(`ClasificacionSolicitud`, en `app/schemas/solicitud.py`) y todo lo demás
—las capas, los errores, las pruebas— está al servicio de esa garantía.

```text
Usuario → FastAPI → Pydantic (valida ENTRADA)
                         ↓
                      Claude
                         ↓
                  Pydantic (valida SALIDA)   ← aquí está el proyecto
                         ↓
                     SQLite → JSON al usuario
```

## Orden real de construcción

Se construyó **de dentro hacia fuera**: primero el contrato de datos, después la
IA, luego la persistencia y al final el HTTP. El motivo está explicado en
`references/02`, y es la lección más transferible de todo el proyecto.

```text
 1. requirements.txt, .gitignore, .env.example   Cimientos y secretos
 2. app/core/config.py                            Configuración
 3. app/schemas/solicitud.py                      ★ EL CONTRATO (Enums)
 4. app/prompts/clasificador.txt                  El prompt
 5. app/core/errors.py                            Errores de dominio
 6. app/services/ia_service.py                    ★ Claude, aislado aquí
 7. app/database/ + models/ + repositories/       Persistencia
 8. app/services/solicitud_service.py             Orquestación
 9. app/api/routes/solicitudes.py                 El endpoint
10. app/main.py                                   Composición y errores HTTP
11. tests/                                        Pruebas
12. README.md, postman/, git                      Documentación y entrega
```

## Comandos que el usuario puede ejecutar ahora

```bash
uvicorn app.main:app --reload     # servidor → http://127.0.0.1:8000/docs
pytest                            # 29 pruebas
pytest -m "not real_api"          # solo las que no gastan tokens
```
