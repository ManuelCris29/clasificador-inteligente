# Clasificador Inteligente de Solicitudes

API REST que recibe solicitudes escritas en lenguaje natural y devuelve una
clasificación **estructurada y validada**: categoría, prioridad, área responsable,
resumen y si requiere intervención humana.

El punto del proyecto no es "llamar a un LLM": es que la respuesta del modelo
**nunca se usa como texto libre**. Todo pasa por un esquema con vocabularios
cerrados antes de persistirse o devolverse.

```text
POST /solicitudes → FastAPI → Pydantic (entrada) → Claude
                                                      ↓
              JSON ← SQLite ← Pydantic (validación) ←─┘
```

---

## Puesta en marcha

Requiere Python 3.11+.

```bash
pip install -r requirements.txt

cp .env.example .env          # Windows: copy .env.example .env
# edita .env y pega tu clave de https://console.anthropic.com

uvicorn app.main:app --reload
```

Documentación interactiva en <http://127.0.0.1:8000/docs>.
Esquema OpenAPI en <http://127.0.0.1:8000/openapi.json>.

### Variables de entorno

| Variable            | Obligatoria | Por defecto                  | Para qué |
|---------------------|-------------|------------------------------|----------|
| `ANTHROPIC_API_KEY` | **Sí**      | —                            | Autenticación con la API de Claude |
| `DATABASE_URL`      | No          | `sqlite:///./solicitudes.db` | Destino de la persistencia |
| `CLAUDE_MODEL`      | No          | `claude-sonnet-5`            | Modelo a usar (ver más abajo) |
| `CLAUDE_MAX_TOKENS` | No          | `1024`                       | Techo de tokens de salida |

`.env` está en `.gitignore`. La API key no aparece en el código fuente ni en las
respuestas de error.

---

## Uso

```bash
curl -X POST http://127.0.0.1:8000/solicitudes \
  -H "Content-Type: application/json" \
  -d '{"texto": "No puedo ingresar al sistema desde esta mañana"}'
```

```json
{
  "id": 1,
  "categoria": "Soporte técnico",
  "prioridad": "alta",
  "area": "TI",
  "resumen": "Usuario no puede acceder al sistema desde esta mañana.",
  "requiere_intervencion_humana": true
}
```

### Valores permitidos

El modelo **no puede devolver nada fuera de estas listas**: son Enums de Pydantic,
y una respuesta que se salga de ellas se rechaza antes de llegar a la base de datos.

| Campo       | Valores |
|-------------|---------|
| `categoria` | `Soporte técnico`, `Recursos humanos`, `Facturación`, `Ventas`, `Administración`, `Otro` |
| `prioridad` | `baja`, `media`, `alta`, `critica` |
| `area`      | `TI`, `Recursos Humanos`, `Finanzas`, `Ventas`, `Administración`, `Servicio al cliente`, `Sin asignar` |

Ante la duda, el sistema usa los valores seguros `Otro` y `Sin asignar` en lugar de
inventar información.

### Errores

| Código | Cuándo |
|--------|--------|
| `400`  | El texto está vacío, ausente, no es texto o supera los 2000 caracteres |
| `502`  | Fallo al hablar con Claude, o su respuesta no es utilizable |
| `500`  | Cualquier otro error inesperado |

Las respuestas de error **nunca** incluyen la API key, el prompt interno ni un
stack trace. El detalle técnico va solo al log del servidor, con el `request_id`
de Anthropic para poder rastrearlo.

Un `502` cuando la respuesta del modelo no valida es deliberado, no un descuido:
el fallo está aguas arriba y el cliente no puede corregirlo reformulando su
petición; un `500` afirmaría que el defecto es de esta aplicación.

---

## Arquitectura

```text
app/
├── main.py                       # composición + traducción de errores a HTTP
├── api/routes/solicitudes.py     # endpoint: solo HTTP
├── schemas/solicitud.py          # Enums cerrados + contratos de entrada/salida
├── services/
│   ├── solicitud_service.py      # orquestación del caso de uso
│   └── ia_service.py             # ← único módulo que conoce el SDK de Anthropic
├── repositories/…                # acceso a datos
├── models/…                      # tablas SQLAlchemy
├── database/…                    # engine y sesiones
├── core/{config,errors}.py       # configuración y errores de dominio
└── prompts/clasificador.txt      # el prompt, fuera del código de negocio
```

La separación existe por una razón concreta: **el LLM está aislado en
`ia_service`**. Cambiar de proveedor, añadir caché, reintentos o procesamiento
asíncrono se hace ahí y en ningún otro sitio.

Dos detalles que no son obvios leyendo el código:

- **El prompt no repite los valores permitidos.** `clasificador.txt` lleva
  marcadores (`{categorias}`, `{areas}`…) que se rellenan desde los Enums. Si la
  lista estuviera escrita a mano en el `.txt`, tarde o temprano diría
  `Facturacion` mientras el validador espera `Facturación`.
- **La sustitución usa `str.replace`, no `str.format`.** El `.txt` está pensado
  para editarse a mano, y `format` fallaría en cuanto alguien escribiera una
  llave literal (por ejemplo, un ejemplo de JSON) en el prompt.

---

## Selección de modelo

`CLAUDE_MODEL` es una variable de entorno; no hay ninguna decisión de modelo
incrustada en el código.

| Modelo | Cuándo usarlo |
|--------|---------------|
| `claude-sonnet-5` | **Por defecto.** Clasificar un texto corto contra un vocabulario cerrado no es una tarea difícil |
| `claude-opus-5` | Tareas complejas: razonamiento de varios pasos, criterios ambiguos, textos largos. Hoy este servicio no tiene ninguna |
| `claude-haiku-4-5` | Ejecutar las pruebas en bucle sin gastar |

Deliberadamente **no** existe un segundo campo "modelo para tareas complejas":
sería configuración que nadie lee mientras el servicio tenga un único caso de uso.

---

## Costo y latencia

Decisiones ya materializadas en el código:

- **Una sola llamada al LLM por solicitud.** Sin reintentos en bucle ni pasadas
  múltiples.
- **La validación ocurre antes de la llamada.** Una entrada inválida cuesta cero
  tokens (hay una prueba que lo verifica).
- **El texto está acotado** a 2000 caracteres.
- **El prompt es corto** (~1.900 caracteres) y sin ejemplos largos.
- **Modelo y `max_tokens` son configurables**, para ajustar costo y latencia sin
  tocar código.

**Recuento de solicitudes procesadas.** No hay un contador en memoria: toda
solicitud clasificada se persiste, así que el número es una consulta y no un
estado que pueda desincronizarse.

```sql
SELECT COUNT(*) FROM solicitudes;                      -- total
SELECT categoria, COUNT(*) FROM solicitudes GROUP BY categoria;
```

Pendiente para más adelante, ya habilitado por la arquitectura: caché de
solicitudes repetidas, procesamiento asíncrono y colas, y una capa de reglas
deterministas previa que evite llamar al LLM cuando no hace falta.

---

## Decisiones técnicas verificadas con Context7

Registro de las decisiones que una consulta a documentación actualizada
determinó, con su motivo y la alternativa descartada.

**Salida estructurada del modelo → `output_config.format` / `messages.parse()`**

- *Motivo:* es el mecanismo nativo vigente del SDK de Anthropic para forzar una
  respuesta conforme a un JSON Schema, y valida el resultado contra ese esquema.
- *Alternativas descartadas:*
  - Forzar JSON mediante `tool_choice` con una herramienta ficticia — patrón
    anterior, hoy innecesario.
  - Prefill del turno `assistant` (empezar la respuesta con `{`) — **devuelve 400**
    en los modelos actuales.
  - El parámetro de nivel superior `output_format`, que está deprecado.
- *Verificación adicional:* se inspeccionó el SDK instalado para confirmar la
  firma real. `ParsedMessage.parsed_output` resultó ser `Optional`, así que el
  código comprueba `None` explícitamente en lugar de asumir que siempre hay
  salida — y también el caso `stop_reason == "refusal"`.

---

## Pruebas

```bash
pytest                       # todo
pytest -m "not real_api"     # solo con dobles: no consume tokens
pytest tests/test_clasificacion.py -v          # clasificación real
pytest tests/test_clasificacion.py::test_soporte_tecnico -v
```

| Archivo | Qué cubre | ¿Llama a Claude? |
|---------|-----------|------------------|
| `tests/test_ia_service.py` | Prompt, manejo de respuestas inutilizables, traducción de errores | No |
| `tests/test_api.py` | Contrato HTTP, códigos 400/502/500, persistencia, OpenAPI | No |
| `tests/test_clasificacion.py` | Los casos de SPEC §21 | **Sí** |

`test_clasificacion.py` se salta solo si no encuentra una API key con prefijo
`sk-ant-`, para que la suite pueda ejecutarse sin credenciales.

**Estado actual: 29/29 pasando**, incluidas las 6 contra la API real.

### Postman

`postman/Clasificador_Inteligente.postman_collection.json` — impórtala y ejecuta
la carpeta con el Collection Runner. Cubre los cinco casos de SPEC §21 más una
prueba de inyección de prompt. La variable `base_url` apunta a
`http://127.0.0.1:8000`.

---

## Preguntas técnicas

**¿Por qué usar IA aquí?** Porque la misma intención se expresa de muchas formas
("no me deja entrar", "el sistema no acepta mi contraseña", "no puedo acceder a mi
cuenta"). Un sistema de palabras clave necesitaría cientos de reglas y seguiría
fallando con la formulación número 101.

**¿Cuándo no usarla?** Cuando una regla determinista basta. `si monto > 1.000.000
→ requiere aprobación` no necesita un LLM: es más caro, más lento y menos fiable
que un `if`.

**¿Cómo se valida la respuesta de un LLM?** Con un esquema. Aquí el JSON Schema de
`ClasificacionSolicitud` se envía a Claude *y* se usa para validar lo que devuelve.
Si no valida, no se persiste nada.

**¿Cómo se evita depender de texto libre?** Con vocabularios cerrados. `categoria`,
`prioridad` y `area` son Enums; un valor inventado es un error de validación, no
una fila rara en la base de datos.

**¿Y si alguien intenta manipular el modelo?** El texto de la solicitud es dato,
no instrucciones — el prompt lo dice explícitamente y va delimitado en una
etiqueta. Pero la garantía real no es el prompt: es el Enum. Aunque el modelo se
dejara convencer, `categoria: "Marketing"` no pasa la validación. Hay una prueba
que lo comprueba.

**¿Limitaciones?** La clasificación es probabilística: puede equivocarse en casos
límite, y la prioridad es un juicio, no un hecho. Por eso las pruebas fijan
categoría y área pero no prioridad. La aplicación depende de un servicio externo,
así que hereda su latencia y su disponibilidad — de ahí el 502 y el aislamiento en
`ia_service`.
