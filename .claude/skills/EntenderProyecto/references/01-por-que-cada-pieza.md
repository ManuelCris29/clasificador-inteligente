# Por qué cada pieza existe

Ninguna decisión aquí es "así se hace". Cada una resuelve un problema concreto.
Si entiendes el problema, sabrás cuándo *no* aplicar la solución.

---

## Por qué usar IA para esto

La misma intención se escribe de infinitas formas:

```text
"No me deja entrar"
"El sistema no acepta mi contraseña"
"No puedo acceder a mi cuenta"
"Login caído desde esta mañana"
```

Un clasificador por palabras clave necesitaría cientos de reglas, y fallaría con
la formulación 101. Un modelo de lenguaje generaliza sin que le enseñes cada
variante.

**Cuándo NO usar IA.** Cuando una regla determinista basta:

```python
if monto > 1_000_000:
    requiere_aprobacion = True
```

Eso no necesita un LLM. Sería más caro, más lento y menos fiable que un `if`.
La regla práctica: **si puedes escribir la condición exacta, escríbela**. La IA
es para cuando no puedes enumerar los casos.

---

## El problema real: el modelo devuelve texto, no datos

Esta es la idea que justifica el 80% del código. Si le pides a Claude que
clasifique y te devuelva JSON, puedes recibir:

```text
"Claro, aquí está la clasificación:\n\n{...}"   ← preámbulo que rompe el parseo
{"categoria": "Facturacion"}                    ← sin tilde
{"categoria": "Reclamos"}                       ← categoría inventada
{"categoria": "Soporte técnico"                 ← JSON incompleto
```

Los cuatro son plausibles. Ninguno debería llegar a la base de datos.

**La solución no es un prompt mejor.** Un prompt reduce la probabilidad, no la
elimina. La solución es una **validación que el modelo no puede saltarse**: un
esquema que rechaza cualquier cosa fuera de lo permitido.

---

## Pydantic: el guardián

Pydantic valida que unos datos cumplan una forma declarada. En este proyecto
hace **dos trabajos distintos** que conviene no confundir:

| Trabajo | Dónde | Protege de |
|---|---|---|
| Validar la **entrada** del usuario | `SolicitudCreate` | Texto vacío, tipos raros, cargas gigantes |
| Validar la **salida** del modelo | `ClasificacionSolicitud` | Categorías inventadas, JSON malformado |

El segundo es el interesante. El primero lo hace cualquier API; el segundo es lo
que convierte esto en un sistema fiable.

```python
class ClasificacionSolicitud(BaseModel):
    categoria: Categoria        # ← Enum: solo 6 valores posibles
    prioridad: Prioridad        # ← Enum: solo 4
    area: AreaResponsable       # ← Enum: solo 7
    resumen: str
    requiere_intervencion_humana: bool
```

Si el modelo devuelve `"Reclamos"`, Pydantic lanza un error. **No es una
comprobación que se pueda olvidar: es el tipo del campo.**

---

## Enum: por qué no un `str`

Podrías declarar `categoria: str` y comprobar después:

```python
if clasificacion.categoria not in CATEGORIAS_VALIDAS:   # ← frágil
    raise ValueError
```

Esa comprobación hay que acordarse de escribirla, en cada sitio donde se use, y
para siempre. Con un Enum, la garantía viaja con el dato:

```python
class Categoria(str, Enum):
    SOPORTE_TECNICO = "Soporte técnico"
    ...
    OTRO = "Otro"
```

Ventajas concretas:

- Un valor inválido es un **error de validación**, no una fila rara en la base.
- El editor autocompleta `Categoria.SOPORTE_TECNICO`; una tilde mal puesta es un
  error visible al escribir, no un bug en producción.
- FastAPI publica los valores permitidos en `/openapi.json` automáticamente.
- Es la defensa real contra **inyección de prompt**: aunque alguien convenza al
  modelo de responder `"Marketing"`, no pasa el Enum.

`(str, Enum)` en lugar de solo `Enum` hace que el miembro *sea* una cadena, así
que se serializa a JSON como `"Soporte técnico"` sin conversiones manuales.

---

## Por qué separar en capas

La estructura no es burocracia: cada capa tiene un motivo verificable.

```text
api/routes/     Solo HTTP. No sabe qué es Claude.
services/       Lógica. No sabe qué es una petición HTTP.
  ia_service    ★ El ÚNICO módulo que importa `anthropic`
repositories/   Solo base de datos. No sabe qué es un LLM.
schemas/        Los contratos. No dependen de nada.
```

**La prueba de que la separación funciona:** cambiar de Claude a otro proveedor
toca *un* archivo. Añadir caché, reintentos o una cola toca *ese mismo* archivo.
Compruébalo:

```bash
grep -rl "import anthropic" app/
# → solo app/services/ia_service.py
```

Si esa lista creciera, la separación se habría roto.

Segundo beneficio, menos obvio: **se puede probar sin gastar dinero**. Como el
endpoint no conoce a Claude, en las pruebas se sustituye `ia_service.clasificar`
por una función falsa y se verifica todo el HTTP sin una sola llamada real.

---

## Por qué el prompt vive en un `.txt`

Si el prompt estuviera dentro de un `.py`, iterarlo significaría tocar código de
negocio, y cada ajuste de redacción sería un cambio arriesgado. En un archivo
aparte, quien mejore el prompt no necesita saber Python.

Pero hay un detalle no evidente: **el `.txt` no repite los valores permitidos**.
Lleva marcadores que se rellenan desde los Enums:

```text
Categoría (elige exactamente uno):
{categorias}
```

Si la lista estuviera escrita a mano en el `.txt`, algún día diría
`Facturacion` mientras el validador espera `Facturación`, y el sistema fallaría
sin que nadie entienda por qué. **Una sola fuente de verdad.**

---

## Por qué las variables de entorno

Una API key en el código fuente acaba en Git, y Git no olvida: borrarla en un
commit posterior no la elimina del historial. Además, la misma aplicación
necesita claves distintas en desarrollo y producción.

```text
.env             ← tu clave real. En .gitignore. Nunca se sube.
.env.example     ← plantilla con marcadores. Sí se sube.
```

Quien clone el repositorio copia `.env.example` a `.env` y pone la suya.

---

## Por qué SQLite

Es un archivo. Sin servidor, sin instalación, sin contraseñas. Perfecto para
empezar. Y como el acceso pasa por SQLAlchemy y la URL está en configuración,
migrar a MySQL es cambiar `DATABASE_URL` y el driver — sin tocar repositorios ni
servicios.

---

## Por qué estos códigos de error

| Código | Cuándo | Quién puede arreglarlo |
|---|---|---|
| `400` | Texto vacío, ausente, demasiado largo | **El cliente**, reformulando |
| `502` | Claude no responde, o responde algo inutilizable | Nadie desde fuera: está aguas arriba |
| `500` | Error inesperado nuestro | El equipo que mantiene esto |

La distinción no es estética: le dice al cliente **si tiene sentido reintentar**.
Un 400 significa "cambia lo que enviaste"; un 502, "vuelve más tarde".

Detalle deliberado: una respuesta de Claude que no valida devuelve **502, no
500**. Podría parecer error nuestro —fuimos nosotros quienes validamos—, pero el
fallo lo causó el proveedor y el cliente no puede corregirlo reformulando.

Y ninguna respuesta de error incluye stack traces, el prompt interno ni la API
key. Un mensaje de error es una superficie por la que se filtra información.
