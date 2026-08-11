# Reconstrúyelo tú, sin IA

Leer código enseña menos que escribirlo. Este es un plan para levantar el
proyecto por tu cuenta, en el mismo orden, con un criterio de "hecho" verificable
en cada etapa.

**Regla del ejercicio:** no copies y pegues del proyecto. Abre el archivo original
solo *después* de intentarlo, para comparar. Lo que buscas no es un archivo
idéntico, sino entender por qué el tuyo se parece o se diferencia.

Haz el proyecto en una carpeta nueva. Idea sugerida para no repetir el mismo
dominio: un **clasificador de tickets de una biblioteca** (categorías:
`Préstamo`, `Devolución`, `Multa`, `Catálogo`, `Otro`).

---

## Etapa 0 — Preparar (15 min)

```bash
mkdir mi-clasificador && cd mi-clasificador
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install fastapi uvicorn[standard] pydantic-settings sqlalchemy anthropic pytest httpx
pip freeze > requirements.txt
```

Crea `.gitignore` **antes** de nada, con `.env` dentro.

✅ **Hecho cuando:** `python -c "import fastapi, anthropic"` no da error.

---

## Etapa 1 — El contrato de datos (45 min)

El corazón. En `app/schemas/ticket.py`:

1. Tres `Enum` con tus vocabularios (recuerda incluir un valor de fallback).
2. `TicketCreate` con validación de longitud **y** un `field_validator` que
   rechace espacios en blanco.
3. `ClasificacionTicket` con `extra="forbid"`.

**Pregúntate:** ¿qué pasa si el modelo devuelve un campo de más? ¿Y si devuelve
la categoría en minúsculas?

✅ **Hecho cuando** este script imprime las tres líneas:

```python
from app.schemas.ticket import TicketCreate, ClasificacionTicket
try: TicketCreate(texto="   ")
except Exception: print("1. espacios rechazados")
try: ClasificacionTicket(categoria="Inventada", ...)
except Exception: print("2. categoria inventada rechazada")
print("3.", ClasificacionTicket.model_json_schema()["properties"].keys())
```

---

## Etapa 2 — Configuración (20 min)

`app/core/config.py` con `BaseSettings`. La API key **obligatoria** (sin valor por
defecto); el resto con valores por defecto.

**Pregúntate:** ¿por qué `get_settings()` lleva `@lru_cache`? Quítalo, añade un
`print` dentro y observa cuántas veces se ejecuta.

✅ **Hecho cuando:** sin `.env`, el programa falla con un mensaje claro; con
`.env`, arranca.

---

## Etapa 3 — El prompt y el servicio de IA (1 h)

La etapa con más aprendizaje.

1. `app/prompts/clasificador.txt` con marcadores, **sin** repetir los valores.
2. `app/services/ia_service.py`:
   - `construir_prompt(texto)` que rellene desde los Enums.
   - `clasificar(texto)` con `messages.parse(output_format=...)`.
   - Comprobar `stop_reason` y que `parsed_output` no sea `None`.
   - Capturar `anthropic.APIError` y relanzar una excepción **propia**.

**Pregúntate:** si `ia_service` lanzara `HTTPException` de FastAPI, ¿qué se
rompería? (Pista: intenta usarlo desde un script de línea de comandos.)

✅ **Hecho cuando:** un script que llame a `clasificar("...")` imprime un objeto
validado. Prueba también con la clave mal puesta y comprueba que el error es
*tuyo*, no del SDK.

---

## Etapa 4 — Persistencia (45 min)

1. `database.py` con `Base`, engine y `get_db`.
2. `models/ticket.py` con la tabla.
3. `repositories/ticket_repository.py` con `guardar(...)`.

**Trampa a propósito:** escribe `default=datetime.now()` (sin lambda), guarda tres
filas y mira las fechas. Después arréglalo. **Ese error lo cometerás en la vida
real; mejor cometerlo ahora.**

**Pregúntate:** ¿por qué el repositorio recibe `ClasificacionTicket` y no un
`dict`?

✅ **Hecho cuando:** guardas una fila y la lees con `sqlite3` desde la terminal.

---

## Etapa 5 — La API (45 min)

1. `services/ticket_service.py` — tres líneas: clasificar, guardar, devolver.
2. `api/routes/tickets.py` — el endpoint con `Depends(get_db)`.
3. `main.py` — la app, el router, el `lifespan` y los manejadores de error.

Escribe los tres manejadores: `RequestValidationError` → 400, tu error de IA →
502, `Exception` → 500.

**Pregúntate:** con el servidor arrancado, envía `{"texto": ""}`. ¿Qué código
sale *antes* de escribir el manejador? (422.) ¿Por qué el SPEC pide 400?

✅ **Hecho cuando:** los cinco casos de prueba responden lo esperado por curl o
Postman, y `/docs` carga.

---

## Etapa 6 — Pruebas (1 h)

Empieza por las que **no** llaman a Claude:

1. `conftest.py` que fije el entorno antes de importar la app.
2. Prueba del prompt: que contenga todos los valores de los Enums.
3. Prueba del endpoint con `monkeypatch` sustituyendo `clasificar`.
4. Pruebas de 400, 502 y 500.

**Pregúntate:** ¿por qué `conftest.py` fija las variables *antes* de los imports?
Muévelo después y observa el error.

✅ **Hecho cuando:** `pytest` pasa sin API key y sin gastar tokens.

---

## Etapa 7 — Entrega (45 min)

README, colección de Postman, y Git con commits temáticos.

Antes de publicar, audita el historial:

```bash
git log --all -p | grep -E "^\+.*sk-ant-api"
```

✅ **Hecho cuando:** clonas tu repo en otra carpeta, sigues tu propio README y
consigues arrancarlo. **Si tu README no basta, no está terminado.**

---

## Los errores que vas a cometer

No son hipotéticos: salieron construyendo este proyecto.

| Error | Síntoma | Por qué pasa |
|---|---|---|
| `default=datetime.now()` sin lambda | Todas las filas con la misma fecha | Se evalúa al importar, una sola vez |
| `str.format` con el prompt | `KeyError` al añadir una llave al `.txt` | `format` interpreta toda llave como marcador |
| Leer configuración al importar | Los tests exigen una API key real | El módulo se evalúa al importarse |
| SQLite `:memory:` sin `StaticPool` | `no such table` en los tests | Cada conexión abre una base vacía distinta |
| Asumir que `parsed_output` existe | `AttributeError` → 500 en vez de 502 | Es `Optional` en el SDK |
| Olvidar `expire_on_commit=False` | Consulta extra al leer `.id` tras el commit | SQLAlchemy invalida el objeto al confirmar |

---

## Cómo saber si de verdad lo entendiste

Responde sin mirar el código:

1. ¿Por qué `ClasificacionSolicitud` tiene que existir antes que `ia_service`?
2. Si Claude devuelve `{"categoria": "Reclamos"}`, ¿dónde falla exactamente y qué
   código HTTP sale?
3. ¿Por qué una respuesta inválida del modelo es 502 y no 500?
4. ¿Por qué 23 de las 29 pruebas no gastan tokens? ¿Qué decisión de arquitectura
   lo permite?
5. ¿Qué comando demuestra que la separación de capas no se ha roto?
6. ¿Por qué el prompt no lista los valores permitidos a mano?
7. Te piden añadir la categoría "Legal". ¿Qué archivos tocas y cuáles no?

Si dudas en alguna, el fichero `references/01` o `references/02` la responde.

---

## Y después

Extensiones ordenadas de menor a mayor dificultad:

1. `GET /solicitudes` con paginación y filtro por categoría.
2. Una capa de reglas deterministas **antes** del LLM (si el texto contiene una
   referencia de factura, ir directo a Facturación sin llamar a Claude).
3. Caché: misma entrada exacta → misma clasificación, sin gastar tokens.
4. Procesamiento asíncrono con una cola, para no bloquear la respuesta.

La 2 y la 3 son especialmente valiosas: enseñan que **la mejor llamada a un LLM
es la que no haces**.
