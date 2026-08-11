# Catálogo de clases y funciones

Todo lo importado de una librería en este proyecto, qué hace y dónde se usa.
Ordenado por librería.

---

## Pydantic — validación de datos

### `BaseModel`

Clase base de la que heredan los modelos de datos. Al heredar, Pydantic valida
los tipos automáticamente al construir el objeto.

```python
from pydantic import BaseModel

class SolicitudCreate(BaseModel):
    texto: str
```

`SolicitudCreate(texto=123)` lanza `ValidationError`. Con una clase normal de
Python, `123` se asignaría sin protestar.

**Métodos que se usan:**

| Método | Qué hace |
|---|---|
| `.model_dump()` | Convierte a `dict` |
| `.model_dump_json()` | Convierte a cadena JSON |
| `.model_validate(obj)` | Construye validando desde un dict u objeto |
| `.model_json_schema()` | Genera el JSON Schema — es lo que se le manda a Claude |

### `Field`

Añade restricciones y metadatos a un campo.

```python
texto: str = Field(..., min_length=5, max_length=2000,
                   description="...", examples=["..."])
```

`...` (Ellipsis) significa **obligatorio**. `description` y `examples` aparecen
en `/docs`.

### `field_validator`

Validación personalizada cuando `Field` no basta.

```python
@field_validator("texto")
@classmethod
def texto_no_vacio(cls, valor: str) -> str:
    limpio = valor.strip()
    if len(limpio) < TEXTO_MIN_LENGTH:
        raise ValueError("...")
    return limpio          # ← devolver el valor transformado
```

Se ejecuta **después** de las validaciones de `Field`. Puede transformar el valor:
lo que devuelve es lo que se guarda.

### `ConfigDict`

Configura el comportamiento de un modelo.

| Opción | Efecto | Dónde se usa |
|---|---|---|
| `extra="forbid"` | Rechaza campos no declarados | `ClasificacionSolicitud` |
| `extra="ignore"` | Los descarta en silencio | `SolicitudResponse` |
| `from_attributes=True` | Permite construir desde un objeto ORM | `SolicitudResponse` |

`extra="forbid"` en la clasificación es deliberado: si el modelo añade un campo
inventado, es un error.

### `BaseSettings` y `SettingsConfigDict` (pydantic-settings)

`BaseSettings` es como `BaseModel`, pero **lee los valores de variables de
entorno** en lugar de argumentos.

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    anthropic_api_key: str          # ← lee ANTHROPIC_API_KEY
```

La correspondencia es automática: atributo en minúsculas → variable en mayúsculas.

---

## Python estándar

### `Enum` y el patrón `(str, Enum)`

```python
from enum import Enum

class Categoria(str, Enum):
    SOPORTE_TECNICO = "Soporte técnico"
```

Heredar de `str` **además** de `Enum` hace que el miembro *sea* una cadena:

```python
Categoria.SOPORTE_TECNICO == "Soporte técnico"   # True
json.dumps({"c": Categoria.SOPORTE_TECNICO})     # funciona sin conversión
```

Sin `str`, habría que escribir `.value` en todas partes.

### `functools.lru_cache`

Guarda el resultado de una función: la segunda llamada con los mismos argumentos
devuelve lo cacheado sin ejecutar el cuerpo.

Se usa **cinco veces**, siempre con el mismo propósito — crear algo caro una sola
vez, de forma perezosa:

| Función | Archivo | Qué evita repetir |
|---|---|---|
| `get_settings()` | `core/config.py` | Releer el `.env` |
| `_plantilla_prompt()` | `services/ia_service.py` | Leer el `.txt` del disco |
| `_cliente()` | `services/ia_service.py` | Crear el cliente HTTP de Anthropic |
| `get_engine()` | `database/database.py` | Crear el engine de SQLAlchemy |
| `get_sessionmaker()` | `database/database.py` | Construir la fábrica de sesiones |

Compruébalo tú: `grep -rn "@lru_cache" app/`

**Por qué "perezoso" importa:** una variable global se evalúa al importar el
módulo. Una función con `lru_cache` se evalúa la primera vez que se *llama*.
Gracias a eso, importar `app.models.solicitud` no exige que exista una API key.

### `pathlib.Path`

Rutas de archivo independientes del sistema operativo.

```python
_RUTA_PROMPT = Path(__file__).resolve().parent.parent / "prompts" / "clasificador.txt"
```

`__file__` es este archivo · `.resolve()` la ruta absoluta · `.parent.parent` sube
dos carpetas · `/` une segmentos. Funciona igual en Windows y Linux.

**Por qué no una ruta relativa como `"app/prompts/..."`:** dependería del
directorio desde el que se lanza el programa.

### `contextlib.asynccontextmanager`

Crea un gestor de contexto asíncrono. FastAPI lo usa para el ciclo de vida:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()      # al arrancar
    yield
                   # al apagar
```

---

## FastAPI

### `FastAPI`

La aplicación.

```python
app = FastAPI(title=..., version=..., description=..., lifespan=lifespan)
```

Esos metadatos aparecen en `/docs`.

### `APIRouter`

Agrupa endpoints relacionados para no tener todo en `main.py`.

```python
router = APIRouter(prefix="/solicitudes", tags=["solicitudes"])
# en main.py:
app.include_router(solicitudes.router)
```

`prefix` se antepone a todas las rutas; `tags` agrupa en la documentación.

### `Depends` — inyección de dependencias

```python
def crear_solicitud(entrada: SolicitudCreate, db: Session = Depends(get_db)):
```

FastAPI ejecuta `get_db()` antes de la función y pasa el resultado. Si `get_db`
usa `yield`, también ejecuta la limpieza después.

**Por qué es útil:** el endpoint no crea la sesión, la *recibe*. En las pruebas se
puede sustituir por otra sin tocar el endpoint.

### `status`

Constantes con nombre en vez de números sueltos.

```python
status.HTTP_200_OK          # 200
status.HTTP_400_BAD_REQUEST # 400
status.HTTP_502_BAD_GATEWAY # 502
```

### `@app.exception_handler(...)`

Registra qué hacer cuando se escapa una excepción de un tipo.

```python
@app.exception_handler(IAServiceError)
async def _fallo_ia(request: Request, exc: IAServiceError):
    return _error(502, exc.mensaje_publico)
```

**El orden importa:** FastAPI busca el manejador del tipo más específico. Como
`RespuestaIAInvalida` hereda de `IAServiceError`, la captura este manejador.

### `RequestValidationError`

La excepción que FastAPI lanza cuando el cuerpo no cumple el schema. Capturarla
permite cambiar el 422 por defecto a 400.

`exc.errors()` devuelve una lista de dicts con `loc` (ruta del campo) y `msg`.

### `JSONResponse`

Respuesta con control total del código y el cuerpo.

```python
JSONResponse(status_code=400, content={"detail": "..."})
```

### `TestClient`

Cliente HTTP para pruebas: ejecuta la app en memoria, sin levantar un servidor.

```python
with TestClient(app, raise_server_exceptions=False) as c:
    r = c.post("/solicitudes", json={"texto": "..."})
```

`raise_server_exceptions=False` hace que un error 500 se devuelva como respuesta
en vez de propagarse — necesario para *probar* el manejador de 500.

---

## SQLAlchemy 2.0

### `DeclarativeBase`

Clase base de los modelos ORM. Todos los que heredan de ella comparten un
registro de tablas.

```python
class Base(DeclarativeBase): ...
class Solicitud(Base): ...
```

### `Mapped[...]` y `mapped_column(...)`

La sintaxis moderna (2.0) para declarar columnas:

```python
id: Mapped[int] = mapped_column(Integer, primary_key=True)
texto_original: Mapped[str] = mapped_column(Text, nullable=False)
```

`Mapped[int]` es la anotación de tipo (para el editor); `mapped_column(...)`
define la columna real.

**Tipos usados:** `Integer`, `String(n)` (longitud máxima), `Text` (sin límite),
`Boolean`, `DateTime(timezone=True)`.

### `create_engine`

Crea la conexión a la base de datos.

```python
create_engine("sqlite:///./solicitudes.db", connect_args={...}, poolclass=...)
```

### `sessionmaker` y `Session`

Una `Session` es una unidad de trabajo. `sessionmaker` es la fábrica.

```python
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
db = SessionLocal()
```

- `autoflush=False`: no envía cambios pendientes a la base automáticamente.
- `expire_on_commit=False`: tras `commit()`, el objeto sigue usable. **Sin esto**,
  leer `solicitud.id` después del commit dispararía otra consulta.

**Métodos usados:** `.add(obj)` lo marca para insertar · `.commit()` confirma ·
`.refresh(obj)` recarga desde la base (para obtener el `id` generado) ·
`.get(Clase, id)` busca por clave primaria · `.close()` libera la conexión.

### `StaticPool`

Fuerza que todas las conexiones sean **la misma**. Solo se usa con SQLite en
memoria, donde cada conexión tendría su propia base vacía.

---

## SDK de Anthropic

### `anthropic.Anthropic`

El cliente.

```python
cliente = anthropic.Anthropic(api_key=...)
```

### `client.messages.parse(...)`

Envía un mensaje **exigiendo salida estructurada**.

```python
respuesta = cliente.messages.parse(
    model="claude-sonnet-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": prompt}],
    output_format=ClasificacionSolicitud,   # ← clase Pydantic
)
```

El SDK convierte la clase en JSON Schema, se lo manda a Claude y valida la
respuesta contra él.

**Diferencia con `messages.create()`:** `create` devuelve texto libre que habría
que parsear a mano; `parse` devuelve un objeto ya validado.

### `ParsedMessage` — el objeto devuelto

| Atributo | Tipo | Cuidado |
|---|---|---|
| `.parsed_output` | `Optional[T]` | **Puede ser `None`** — comprobar siempre |
| `.stop_reason` | `str` | `"end_turn"`, `"refusal"`, `"max_tokens"`… |
| `.content` | lista de bloques | El detalle en crudo |
| `.usage` | objeto | Tokens consumidos |

Que `parsed_output` sea `Optional` es la razón de las dos comprobaciones en
`clasificar()`. **Se descubrió inspeccionando el SDK instalado, no de memoria.**

### `anthropic.APIError` y sus subclases

Raíz de los errores del SDK. Capturarla cubre todos:

| Excepción | Cuándo |
|---|---|
| `AuthenticationError` | 401 — clave inválida |
| `BadRequestError` | 400 — petición mal formada **o sin saldo** |
| `RateLimitError` | 429 — demasiadas peticiones |
| `APIConnectionError` | Fallo de red (sin respuesta HTTP) |

**Atributos útiles:** `.status_code` y `.request_id` — pero **no existen en todas**
(`APIConnectionError` no llega a tener respuesta), de ahí el `getattr` con
defecto.

---

## pytest

### `@pytest.fixture`

Prepara algo que varias pruebas necesitan. La prueba lo pide por nombre:

```python
@pytest.fixture
def client():
    init_db()
    with TestClient(app) as c:
        yield c            # ← lo posterior al yield es la limpieza

def test_algo(client):     # ← pytest inyecta el fixture
    ...
```

### `monkeypatch`

Fixture integrado que sustituye atributos **y los restaura al terminar**.

```python
monkeypatch.setattr(ia_service, "clasificar", _falso)
```

Es lo que permite probar todo el sistema sin llamar a Claude. La restauración
automática evita que una prueba contamine a la siguiente.

### `@pytest.mark.parametrize`

Ejecuta la misma prueba con distintos datos.

```python
@pytest.mark.parametrize("payload", [
    pytest.param({"texto": ""}, id="texto-vacio"),
    pytest.param({}, id="campo-ausente"),
])
def test_entrada_invalida_devuelve_400(client, payload):
```

Cada caso aparece como una prueba independiente con su `id`.

### `pytest.raises`

Afirma que algo lanza una excepción.

```python
with pytest.raises(RespuestaIAInvalida):
    ia_service.clasificar("...")
```

### `pytest.skip` y marcadores

```python
pytestmark = pytest.mark.real_api          # marca todo el archivo
pytest.skip("Sin API key real...")         # se salta en tiempo de ejecución
```

Los marcadores se declaran en `pytest.ini` y permiten `pytest -m "not real_api"`.
