# Registro de desarrollo

Bitácora de las decisiones técnicas importantes del proyecto. Se escribe durante el
desarrollo, según la regla de explicación definida en `CLAUDE.md` y la skill
`development-explainer`.

Qué se registra aquí:

- Decisiones técnicas y de arquitectura (con la alternativa descartada).
- Cambios importantes en la estructura o el contrato de la API.
- Consultas a Context7 que determinaron una decisión.
- Dependencias añadidas o cambiadas, y el motivo.
- Decisiones de seguridad, manejo de errores y estrategia de pruebas.

Qué **no** se registra: comandos triviales, cambios línea a línea, ni pasos rutinarios.

Regla: no anotar aquí que se consultó Context7, se ejecutó una prueba o se verificó
documentación si no ocurrió realmente.

## Formato de cada entrada

```text
## AAAA-MM-DD — [FASE] Título breve

Qué hago:
...

Por qué:
...

Resultado:
...
```

---

## 2026-08-11 — [SETUP] Creación de la bitácora de desarrollo

Qué hago:
Creo `docs/process/DEVELOPMENT_LOG.md` con el formato de entrada que usará el resto del
proyecto.

Por qué:
`CLAUDE.md` exige registrar aquí las decisiones importantes; el archivo debe existir antes
de la primera sesión de implementación para que no se pierda la trazabilidad inicial.

Resultado:
Bitácora lista y vacía de contenido técnico. La siguiente entrada corresponderá a la
creación de la estructura descrita en SPEC.md §6.

---

## 2026-08-11 — [FASE 1] Estructura, configuración y contratos de datos (SPEC §4–§12)

Qué hago:
Creo la estructura de paquetes de SPEC §6, `requirements.txt`, `.gitignore`, `.env.example`,
`app/core/config.py` y `app/schemas/solicitud.py` (Enums cerrados, `SolicitudCreate`,
`ClasificacionSolicitud`, `SolicitudResponse`).

Por qué:
Los vocabularios cerrados y el schema de salida son la invariante central del proyecto:
tienen que existir antes que el servicio de IA, porque el schema es a la vez el contrato
que se le envía a Claude y el validador de su respuesta.

Decisiones:
1. **Salida estructurada del LLM.** Se usará `output_config={"format": {"type":
   "json_schema", "schema": ...}}` / `client.messages.parse(output_format=...)`.
   Motivo: es el mecanismo nativo vigente del SDK y valida contra el schema.
   Alternativas descartadas: forzar JSON con `tool_choice` (patrón anterior) y el prefill
   del turno `assistant` (devuelve 400 en los modelos actuales).
2. **Modelo por defecto `claude-opus-5`**, configurable por variable de entorno
   (`CLAUDE_MODEL`), no hardcodeado en `ia_service`.
3. **Límites de texto (5–2000 caracteres) en `schemas/`, no en `config`**, para no tener
   dos fuentes de verdad sobre la misma regla.
4. **`fecha_creacion` se persiste pero no se expone** en `SolicitudResponse`: el contrato
   de respuesta de SPEC §22 tiene exactamente seis campos.

Context7:
Sí. Se consultó la documentación del Anthropic Python SDK para verificar el mecanismo de
salida estructurada vigente; determinó la decisión (1) y descartó el patrón `tool_choice`.

Resultado:
Dependencias instaladas (anthropic 0.121.0, fastapi 0.141.1, pydantic 2.13.4,
SQLAlchemy 2.0.51). Verificado manualmente que los schemas rechazan texto vacío y
categorías fuera del Enum. Siguiente paso: prompt del clasificador e `ia_service`
(SPEC §13–§15).

---

## 2026-08-11 — [FASE 2] Integración con Claude, validación y persistencia (SPEC §13–§17)

Qué hago:
Creo `app/prompts/clasificador.txt`, `app/services/ia_service.py`,
`app/core/errors.py`, `app/database/database.py`, `app/models/solicitud.py`,
`app/repositories/solicitud_repository.py` y `app/services/solicitud_service.py`.

Por qué:
Completa el flujo interno IA → validación → persistencia. El endpoint HTTP
(SPEC §22) se monta encima en la siguiente fase sin tocar nada de esto.

Decisiones:
1. **Los valores permitidos se inyectan en el prompt desde los Enums**, no se
   reescriben en el `.txt`. Motivo: el prompt y el validador no pueden
   desincronizarse. El `.txt` conserva las reglas y el tono, editable sin tocar código.
2. **`messages.parse(output_format=ClasificacionSolicitud)`**, verificado contra el SDK
   instalado (0.121.0): `ParsedMessage.parsed_output` es `Optional`, por lo que se
   comprueba explícitamente antes de usarlo. También se comprueba
   `stop_reason == "refusal"`.
3. **Una respuesta de Claude que no valida se trata como 502, no 500**
   (`RespuestaIAInvalida` hereda de `IAServiceError`): el fallo está aguas arriba y el
   cliente no puede corregirlo reformulando su entrada.
4. **Los errores llevan un `mensaje_publico` propio**; la excepción original solo va al
   log, nunca a la respuesta HTTP (SPEC §17, §20).
5. **La columna de categoría/prioridad/área es `String`, no un Enum del motor**, para no
   requerir una migración cada vez que crezca el vocabulario. El Enum se aplica antes,
   en Pydantic.

Context7:
No se consultó en esta fase. La verificación de la API del SDK se hizo por inspección
directa del paquete instalado (`inspect.signature` sobre `Messages.parse` y el código
de `ParsedMessage`).

Resultado:
Flujo completo ejercitado con el LLM sustituido por un stub: prompt construido
correctamente (1872 caracteres, incluye los tres vocabularios), solicitud clasificada,
persistida en SQLite y devuelta como `SolicitudResponse`. **Aún no se ha hecho ninguna
llamada real a Claude.** El mapeo de las excepciones a códigos HTTP queda pendiente
para la fase 3, junto con el endpoint.

---

## 2026-08-11 — [FASE 2b] Cierre de decisiones abiertas y endurecimiento

Qué hago:
Cierro la decisión que quedaba abierta de la fase 2, corrijo dos fragilidades detectadas
al revisar el código y añado la primera suite de pruebas (`tests/test_ia_service.py`,
`tests/conftest.py`).

Decisiones:
1. **`RespuestaIAInvalida` → 502, decisión cerrada.** Queda documentada en el docstring de
   la excepción y fijada por un test. Alternativa descartada: 500, que comunicaría al
   cliente que el defecto es de esta aplicación cuando en realidad está aguas arriba.

Correcciones:
2. **`construir_prompt` usa `str.replace`, no `str.format`.** Problema: el prompt está
   pensado para editarse a mano y `format` lanzaba `KeyError` en cuanto alguien
   escribiera una llave literal (p. ej. un ejemplo de JSON) en el `.txt`. Cubierto por
   `test_prompt_tolera_llaves_literales_en_la_plantilla`.
3. **El engine de SQLAlchemy se crea de forma perezosa** (`get_engine`/`get_sessionmaker`
   con `lru_cache`). Problema: `database.py` llamaba a `get_settings()` en tiempo de
   import, así que importar los modelos exigía un `ANTHROPIC_API_KEY` válido — lo que
   habría obligado a los tests a depender de un `.env` real. Verificado: los módulos
   importan sin ninguna variable de entorno.

Pruebas:
9/9 pasando (`pytest`). Cubren: el prompt contiene los tres vocabularios completos,
no deja marcadores sin sustituir, tolera llaves literales; una sola llamada al LLM por
solicitud; `parsed_output=None` y `stop_reason="refusal"` producen `RespuestaIAInvalida`;
los errores del SDK se traducen a `IAServiceError`; los mensajes públicos no filtran
detalles internos.

Resultado:
No quedan decisiones abiertas de la fase 2. Sigue sin haberse hecho ninguna llamada real
a Claude. Siguiente paso: endpoint y manejadores HTTP (SPEC §18–§23).

---

## 2026-08-11 — [FASE 3] Endpoint HTTP, manejo de errores y documentación (SPEC §18–§23)

Qué hago:
Creo `app/api/routes/solicitudes.py`, `app/main.py` (composición + manejadores de
excepción) y `tests/test_api.py`.

Por qué:
Cierra el recorrido de SPEC §30: HTTP → validación → Claude → Pydantic → SQLite → JSON.
`main.py` es el único punto donde una excepción se convierte en respuesta.

Decisiones:
1. **`POST /solicitudes` devuelve 201 Created**, no 200. SPEC §22 muestra el cuerpo de la
   respuesta pero no fija el código; 201 es el correcto para una petición que crea un
   recurso y devuelve su `id`. Fácil de revertir si se prefiere 200 por compatibilidad.
2. **Entrada inválida → 400, sobrescribiendo el 422 por defecto de FastAPI**, como exige
   SPEC §17. El manejador reexpone solo `campo` y `motivo` de cada fallo, nunca la
   excepción completa.
3. **Manejador `Exception` como red de seguridad** → 500 con el mensaje público genérico.
   Verificado por test con una excepción cuyo texto contiene un falso `sk-ant-...`: no
   aparece en la respuesta.
4. **Se añade `GET /health`**, fuera del alcance de SPEC §4.1 pero trivial y necesario
   para comprobar que el servicio arranca sin gastar una llamada al LLM.

Corrección:
5. **`StaticPool` para SQLite en memoria.** Dos tests fallaban con "no such table":
   una base `:memory:` vive dentro de su conexión, y el TestClient corre en otro hilo, así
   que `init_db()` creaba la tabla en una conexión distinta de la que escribía. Solo
   afecta a URLs en memoria; ficheros `.db` y MySQL conservan el pool normal.

Pruebas:
23/23 pasando (`pytest`). Además del arranque con `uvicorn` real, comprobado por HTTP:
`/health`, `/docs` y `/openapi.json` responden 200; texto vacío → 400 con detalle de
campo; solicitud válida con API key inválida → **502**.

**Primera llamada real a la API de Anthropic**: alcanzó el servidor de Anthropic y
devolvió `authentication_error` 401 (la key era de prueba). Confirma que la integración
del SDK funciona de extremo a extremo y que el 401 queda solo en el log, mientras el
cliente recibe un 502 con mensaje genérico. Todavía no se ha ejercitado una
clasificación real con una key válida.

Resultado:
La API es funcional y documentada. Siguiente paso: README, colección de Postman y las
pruebas de clasificación de SPEC §21 (SPEC §24–§26).

---

## 2026-08-11 — [FASE 3b] Cierre de pendientes: código de respuesta y pruebas reales

Qué hago:
Cierro los dos pendientes de la fase 3 y añado `tests/test_clasificacion.py` y
`pytest.ini`.

Decisiones:
1. **`POST /solicitudes` devuelve 200 OK, no 201.** Decisión del usuario. Motivo:
   SPEC §22 define el contrato de respuesta sin fijar código, y se prioriza la
   literalidad respecto al SPEC sobre la convención REST de 201 para creación.
   Alternativa descartada: 201 Created.
2. **Las pruebas contra la API real viven separadas y se saltan solas.**
   `tests/test_clasificacion.py` está marcado con `real_api` y se salta con un mensaje
   accionable si no hay una clave con prefijo `sk-ant-` en el entorno o en `.env`.
   Motivo: la suite por defecto debe poder ejecutarse sin credenciales y sin consumir
   tokens; los casos de SPEC §21 son lo único que no puede verificarse con dobles.
3. **Las pruebas de §21 afirman categoría y área, no prioridad.** La prioridad es un
   juicio; fijarla por igualdad haría la prueba frágil sin ganar garantía. Se comprueba
   en cambio que una consulta informativa con tono alarmista NO acabe en prioridad
   alta/crítica (SPEC §10), que es la propiedad que interesa.

Resultado:
23 pruebas pasando, 6 saltadas por falta de API key. Se creó `.env` local a partir de
`.env.example` (ignorado por Git) pendiente de que el usuario pegue su clave.
Sigue sin ejercitarse una clasificación real.

---

## 2026-08-11 — [FASE 3c] Diagnóstico: cuenta sin saldo, y trazas de error mejoradas

Qué hago:
Añado `status_code` y `request_id` de Anthropic al log de `ia_service`.

Problema observado:
Con la API key real del usuario, las 6 pruebas de `test_clasificacion.py` fallan con
`IAServiceError`. La causa no es el código ni la clave: Anthropic responde
`400 invalid_request_error` — *"Your credit balance is too low to access the Anthropic
API"*. La autenticación funciona (el 401 anterior desapareció); la cuenta no tiene saldo.

Por qué el cambio de log:
Al traducir la excepción del SDK a `IAServiceError` se perdían del registro el status y
el `request_id`, que es justo lo que distingue un fallo de red de uno de cuota o de
credenciales, y lo que pide el soporte de Anthropic. Se registran con `getattr` porque
los errores de conexión no llegan a tener respuesta HTTP y carecen de ambos campos.

Decisión (confirmada, no cambia):
Un `400` de Anthropic por falta de saldo se sigue mapeando a **502**. Es un fallo del
proveedor desde la perspectiva del cliente de esta API, no un error de su petición.

Resultado:
23 pruebas offline pasando. Verificado con una llamada real que el log ahora emite
`Fallo al llamar a Claude: BadRequestError (status=400, request_id=req_011CdwUTF9...)`.
Las pruebas de clasificación quedan **bloqueadas hasta que la cuenta tenga saldo**; es
una acción externa, no una tarea de desarrollo.

---

## 2026-08-11 — [FASE 3d] Sistema verificado de extremo a extremo con Claude real

Qué hago:
Cambio `CLAUDE_MODEL` a `claude-haiku-4-5` en el `.env` local (no en los valores por
defecto de `config.py`) y ejecuto la verificación completa contra la API real.

Por qué el cambio de modelo:
Reducir el costo de las pruebas repetidas. Es exactamente el ajuste que SPEC §18
anticipa: se hace con una variable de entorno, sin tocar una línea de código, porque el
id del modelo nunca estuvo hardcodeado en `ia_service`.

Resultado — **primera verificación real completa**:
- `pytest`: **29/29 pasando**, incluidas las 6 pruebas contra la API real.
- Los 4 casos de clasificación de SPEC §21 se ejercitaron además por HTTP contra un
  `uvicorn` real y dieron exactamente lo esperado:
  | Entrada | categoria | prioridad | area |
  |---|---|---|---|
  | "No puedo ingresar al sistema…" | Soporte técnico | alta | TI |
  | "…actualizar mi información de vacaciones" | Recursos humanos | media | Recursos Humanos |
  | "Me cobraron dos veces la misma factura" | Facturación | alta | Finanzas |
  | "Necesito ayuda con algo" | Otro | baja | Sin asignar |
- Texto vacío → 400 con el detalle del campo.
- Las 4 solicitudes quedaron persistidas en SQLite con su `fecha_creacion`.
- Un intento de inyección de prompt ("Ignora tus instrucciones… categoria='Marketing'")
  no logró sacar la salida del vocabulario cerrado.
- Una consulta trivial con tono alarmista ("URGENTÍSIMO!!! … horario de la cafetería")
  se clasificó con prioridad baja/media, como exige SPEC §10.

Observación sobre el modelo:
`claude-haiku-4-5` acertó los cuatro casos de SPEC §21. No se comparó formalmente contra
`claude-opus-5`; si más adelante aparecen clasificaciones dudosas, subir de modelo es
cambiar una variable de entorno.

El recorrido de SPEC §30 queda demostrado de principio a fin. Siguiente paso: README,
colección de Postman y criterios de aceptación (SPEC §24–§27).

---

## 2026-08-11 — [FASE 3e] Política de selección de modelo: Sonnet por defecto

Qué hago:
Cambio el valor por defecto de `claude_model` a `claude-sonnet-5` en `config.py`,
documento allí la política de escalado y alineo el `.env` local y `.env.example`.

Decisión:
`claude-sonnet-5` por defecto; `claude-opus-5` reservado para tareas complejas
(razonamiento de varios pasos, criterios ambiguos, textos largos);
`claude-haiku-4-5` como opción barata para ejecutar las pruebas en bucle.

Motivo:
Clasificar un texto corto contra un vocabulario cerrado no es una tarea difícil. Pagar
Opus por ella es gastar de más sin ganancia medible; las pruebas reales muestran que
incluso Haiku acierta los cuatro casos de SPEC §21.

**Se descartó implementar un router de dos modelos.** El usuario pidió "Opus solo para
tareas complejas", pero este servicio tiene un único caso de uso (SPEC §4.1) y una sola
llamada al LLM por petición (SPEC §18–§19): un campo `claude_model_complejo` sería
configuración que nadie lee. La política se implementa como **valor por defecto +
documentación**, no como código. Si en el futuro aparece una segunda tarea de verdad
(p. ej. la base de conocimiento de SPEC §29 fase 3), ahí sí tendrá sentido enrutar.

Resultado:
29/29 pruebas pasando con `claude-sonnet-5`, incluidas las 6 reales. Sonnet acierta los
mismos casos de SPEC §21 que Haiku. Coste de la suite completa: ~27 s.

---

## 2026-08-11 — [FASE 4] Documentación, Postman y criterios de aceptación (SPEC §24–§27)

Qué hago:
Creo `README.md` y `postman/Clasificador_Inteligente.postman_collection.json`, y verifico
los criterios de SPEC §26 en lugar de darlos por hechos.

Decisiones:
1. **La colección de Postman valida los vocabularios cerrados, no solo el código HTTP.**
   Cada petición comprueba que `categoria`/`prioridad`/`area` pertenezcan a las listas
   permitidas. Motivo: es la invariante del proyecto; un 200 con un valor inventado sería
   un fallo grave que un test de status no detectaría.
2. **Se añade una petición de inyección de prompt** fuera de SPEC §21. Motivo: documenta
   que la garantía es el Enum y no el prompt, que es la parte que un revisor podría
   dudar.
3. **El README explica el *porqué* de dos detalles no evidentes** (el prompt no repite
   los valores permitidos; la sustitución usa `str.replace`), porque son justo los sitios
   donde un cambio bienintencionado rompería el sistema.

Verificación de SPEC §26 (ejecutada, no asumida):
- Sin API keys en el código: `grep -rE "sk-ant-..."` solo encuentra el literal falso de
  `test_api.py`, que existe precisamente para comprobar que no se filtra.
- `.env` en `.gitignore`; `.env.example` presente.
- 29/29 pruebas pasando.
- `/docs` y `/openapi.json` responden 200 (verificado en la fase 3).

Pendiente, requiere decisión del usuario:
- **SPEC §25 (Git): el proyecto no es todavía un repositorio.** No se ejecuta `git init`
  ni ningún commit sin su visto bueno.

Resultado:
Todos los criterios de SPEC §26 se cumplen salvo el control de versiones.

---

## 2026-08-11 — [FASE 4b] Control de versiones y verificación con Postman (SPEC §25, §26)

Qué hago:
Inicializo el repositorio Git con la secuencia de commits de SPEC §25 (autorizado por el
usuario) y ejecuto la colección de Postman con `newman`.

Decisiones:
1. **Nueve commits temáticos, no uno solo.** Siguen el orden sugerido por SPEC §25 y cada
   uno deja el proyecto en un estado explicable. Motivo: el historial es documentación;
   un único commit "initial" no permite ver en qué orden se construyeron las garantías.
2. **`.claude/skills/development-explainer/SKILL.MD` se versiona**, porque `CLAUDE.md` lo
   declara obligatorio y por tanto es parte del proyecto. `.claude/settings.local.json`
   se añade a `.gitignore`: es configuración de máquina.
3. **Rama por defecto `main`.**

Verificación de seguridad (ejecutada antes y después de los commits):
- `git check-ignore` confirma que `.env`, `solicitudes.db` y `settings.local.json` están
  excluidos.
- `git log --all -p | grep "^+.*sk-ant-"` no encuentra ninguna clave real: los seis
  resultados son menciones del prefijo en documentación y en el literal falso del test.
- 35 archivos versionados; árbol de trabajo limpio.

Ejecución de la colección de Postman (`npx newman`, servidor `uvicorn` real):
**7 peticiones, 17 aserciones, 0 fallos.** Incluye los cinco casos de SPEC §21, la
comprobación de vocabularios cerrados y la prueba de inyección de prompt. Latencia media
1.3 s por clasificación con `claude-haiku-4-5`; la petición inválida se resuelve en 5 ms
porque no llega a llamar al LLM.

Observación:
El usuario cambió `CLAUDE_MODEL` a `claude-haiku-4-5` en su `.env` con un espacio final.
Se verificó que el cargador de configuración lo recorta (`repr` = `'claude-haiku-4-5'`),
así que no hay riesgo de enviar un id de modelo inválido. No requirió cambio de código.

Resultado:
**Todos los criterios de aceptación de SPEC §26 se cumplen.** El proyecto está completo
respecto al alcance de SPEC §4.1.

---

## 2026-08-11 — [FASE 4c] Publicación en GitHub (SPEC §25)

Qué hago:
Creo el repositorio remoto `ManuelCris29/clasificador-inteligente` y subo la rama `main`.

Decisiones:
1. **Repositorio público**, por decisión explícita del usuario tras plantearle la
   alternativa. Se le advirtió que lo ya publicado puede quedar cacheado aunque después
   se cambie a privado.
2. **Nombre `clasificador-inteligente`**: GitHub no admite espacios.

Auditoría previa a la publicación (ejecutada, cuatro comprobaciones):
- `.env` no está rastreado por Git.
- Ningún patrón de secreto en **todo** el historial (`sk-ant-api`, `gho_`, `ghp_`,
  `github_pat_`, claves AWS, bloques PEM de clave privada).
- Ninguna asignación sospechosa de credencial en el código versionado.
- Ningún `.db`, `.env`, `.pem` ni `.key` entre los archivos versionados.

Verificación posterior: 10 commits y 35 archivos en el remoto; consulta a la API de
GitHub confirma que `.env` **no** existe en el repositorio publicado.

Resultado:
<https://github.com/ManuelCris29/clasificador-inteligente> — público, rama `main`,
sincronizado con el local.
