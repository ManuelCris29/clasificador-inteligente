# SPEC — Proyecto 1: Clasificador Inteligente de Solicitudes

**Versión:** 1.0
**Día:** 1 — Automatización e integración con IA
**Estado:** Pendiente de implementación
**Tipo:** Proyecto práctico de integración con IA

---

## 1. Objetivo

Construir una API capaz de recibir solicitudes escritas en lenguaje natural y utilizar un modelo de IA para:

1. Clasificar la solicitud.
2. Determinar su prioridad.
3. Identificar el área responsable.
4. Extraer información relevante.
5. Generar un resumen.
6. Determinar si requiere intervención humana.
7. Generar una respuesta inicial estructurada.

El sistema debe entregar siempre una respuesta **estructurada y validada**, evitando depender directamente del texto libre generado por el modelo.

---

## 2. Problema

Una empresa recibe solicitudes de usuarios a través de diferentes canales.

Actualmente, un empleado debe leer manualmente cada solicitud para determinar:

* Qué tipo de solicitud es.
* Qué tan urgente es.
* Qué área debe atenderla.
* Qué información contiene.
* Si requiere intervención humana.

Este proceso consume tiempo y puede producir errores de clasificación.

---

## 3. Solución propuesta

Construir un servicio backend que utilice IA para analizar automáticamente cada solicitud.

### Flujo general

```text
Usuario
   │
   ▼
POST /solicitudes
   │
   ▼
FastAPI
   │
   ▼
Validación de entrada
   │
   ▼
Claude API
   │
   ▼
Clasificación + extracción
   │
   ▼
Validación Pydantic
   │
   ▼
Persistencia
   │
   ▼
Respuesta JSON
```

---

# 4. Alcance

## 4.1 Incluido

El proyecto debe implementar:

* API REST con FastAPI.
* Endpoint `POST /solicitudes`.
* Validación de entrada con Pydantic.
* Integración con Claude API.
* Clasificación mediante IA.
* Extracción de información estructurada.
* Validación de la respuesta de IA.
* Persistencia de solicitudes.
* Manejo básico de errores.
* Configuración mediante variables de entorno.
* Pruebas básicas.
* Documentación de la API.
* README.
* Colección de pruebas para Postman.

## 4.2 No incluido

En esta primera versión NO se implementará:

* WhatsApp.
* Telegram.
* Interfaz web.
* Sistema de autenticación completo.
* Panel administrativo.
* Sistema de tickets.
* Automatización de correo.
* Despliegue en AWS.
* Entrenamiento o fine-tuning de modelos.

Estos elementos podrán incorporarse posteriormente.

---

# 5. Stack tecnológico

| Tecnología | Propósito                 |
| ---------- | ------------------------- |
| Python     | Lenguaje principal        |
| FastAPI    | API REST                  |
| Claude API | Procesamiento inteligente |
| Pydantic   | Validación y esquemas     |
| SQLite     | Persistencia inicial      |
| SQLAlchemy | Acceso a base de datos    |
| Postman    | Pruebas de API            |
| Git        | Control de versiones      |
| GitHub     | Repositorio               |

La base de datos podrá migrarse posteriormente de SQLite a MySQL.

---

# 6. Arquitectura propuesta

La aplicación debe mantener separación entre responsabilidades.

```text
app/
│
├── main.py
│
├── api/
│   └── routes/
│       └── solicitudes.py
│
├── schemas/
│   └── solicitud.py
│
├── services/
│   ├── ia_service.py
│   └── solicitud_service.py
│
├── models/
│   └── solicitud.py
│
├── repositories/
│   └── solicitud_repository.py
│
├── database/
│   └── database.py
│
├── core/
│   └── config.py
│
└── prompts/
    └── clasificador.txt
```

La estructura podrá modificarse durante la implementación si existe una razón técnica justificada.

---

# 7. Modelo de entrada

Endpoint:

```http
POST /solicitudes
```

Request:

```json
{
  "texto": "No puedo ingresar al sistema desde esta mañana"
}
```

### Schema esperado

```python
class SolicitudCreate(BaseModel):
    texto: str
```

La API debe rechazar solicitudes cuyo texto esté vacío o no cumpla las validaciones definidas.

---

# 8. Modelo de salida

La respuesta debe estar estructurada mediante Pydantic.

Ejemplo:

```json
{
  "id": 1,
  "categoria": "Soporte técnico",
  "prioridad": "alta",
  "area": "TI",
  "resumen": "Usuario no puede acceder al sistema",
  "requiere_intervencion_humana": true
}
```

---

# 9. Categorías

Inicialmente se utilizarán las siguientes categorías:

```text
Soporte técnico
Recursos humanos
Facturación
Ventas
Administración
Otro
```

El modelo NO debe inventar nuevas categorías.

Si una solicitud no corresponde claramente a ninguna categoría:

```text
categoria = "Otro"
```

---

# 10. Prioridades

La prioridad debe pertenecer exclusivamente a:

```text
baja
media
alta
critica
```

### Criterios generales

**Baja**

Solicitud informativa o que puede esperar.

**Media**

Problema que afecta al usuario, pero existe una alternativa o no requiere atención inmediata.

**Alta**

Problema que impide realizar una actividad importante.

**Crítica**

Problema que puede afectar múltiples usuarios, operaciones críticas o servicios esenciales.

La IA debe basar la prioridad en el contenido de la solicitud y no simplemente en palabras como "urgente".

---

# 11. Áreas responsables

El área debe pertenecer exclusivamente a:

```text
TI
Recursos Humanos
Finanzas
Ventas
Administración
Servicio al cliente
Sin asignar
```

Si la IA no puede determinar razonablemente el área:

```text
area = "Sin asignar"
```

---

# 12. Respuesta estructurada del modelo

La IA debe producir exclusivamente información compatible con el siguiente esquema conceptual:

```python
class ClasificacionSolicitud(BaseModel):

    categoria: Categoria

    prioridad: Prioridad

    area: AreaResponsable

    resumen: str

    requiere_intervencion_humana: bool
```

No se debe utilizar directamente una respuesta de texto libre del modelo como resultado final.

---

# 13. Integración con Claude

La aplicación debe utilizar Claude como componente de análisis.

Flujo:

```text
Solicitud
    ↓
Construcción del prompt
    ↓
Claude API
    ↓
Respuesta estructurada
    ↓
Pydantic
    ↓
Resultado válido
```

La API Key debe almacenarse mediante una variable de entorno.

Ejemplo:

```env
ANTHROPIC_API_KEY=...
```

Nunca se debe colocar la API Key directamente en el código fuente.

---

# 14. Prompt del clasificador

El prompt debe indicar explícitamente:

* Rol del modelo.
* Objetivo.
* Categorías permitidas.
* Prioridades permitidas.
* Áreas permitidas.
* Formato esperado.
* Prohibición de inventar categorías.
* Qué hacer cuando no existe suficiente información.
* Que la salida debe ser estructurada.

Ejemplo conceptual:

```text
Eres un clasificador de solicitudes empresariales.

Analiza la solicitud proporcionada.

Debes clasificarla utilizando únicamente los valores
permitidos para categoría, prioridad y área.

No inventes valores.

Si no existe suficiente información para determinar
el área responsable, utiliza "Sin asignar".

Genera también un resumen breve.

Determina si la solicitud requiere intervención humana.
```

El prompt definitivo debe mantenerse separado del código de negocio.

---

# 15. Validación

La respuesta generada por Claude debe considerarse **no confiable hasta ser validada**.

El flujo debe ser:

```text
Claude
  ↓
Respuesta recibida
  ↓
Parseo
  ↓
Pydantic
  ↓
¿Es válida?
 ├── Sí → continuar
 │
 └── No → manejar error
```

Nunca se debe guardar directamente una respuesta del LLM en la base de datos sin validación.

---

# 16. Persistencia

Cada solicitud procesada debe almacenarse.

Información mínima:

```text
id
texto_original
categoria
prioridad
area
resumen
requiere_intervencion_humana
fecha_creacion
```

Ejemplo:

```text
Solicitud
├── id
├── texto_original
├── categoria
├── prioridad
├── area
├── resumen
├── requiere_intervencion_humana
└── fecha_creacion
```

---

# 17. Manejo de errores

La API debe manejar como mínimo:

### Error de entrada

```http
400 Bad Request
```

Cuando los datos proporcionados sean inválidos.

### Error de Claude

```http
502 Bad Gateway
```

Cuando exista un problema al comunicarse con el proveedor de IA.

### Error interno

```http
500 Internal Server Error
```

Para errores inesperados.

Los errores no deben exponer:

* API Keys.
* Stack traces.
* Información sensible.
* Prompts internos.

---

# 18. Control de costos

La aplicación debe considerar el costo asociado al uso de modelos de IA.

Se deben implementar o documentar estrategias como:

* Prompts pequeños.
* Evitar enviar información innecesaria.
* Limitar longitud de solicitudes.
* Utilizar el modelo adecuado para cada tarea.
* Evitar llamadas duplicadas.
* Registrar cantidad de solicitudes procesadas.

Como mejora futura:

```text
Solicitud
   ↓
¿Se puede resolver con reglas?
   ├── Sí → No llamar IA
   │
   └── No → Claude
```

---

# 19. Latencia

La integración debe diseñarse considerando que una llamada a un modelo externo agrega latencia.

El código debe evitar:

* Llamadas innecesarias.
* Múltiples llamadas para una misma solicitud.
* Procesamiento redundante.

La arquitectura debe permitir posteriormente implementar:

* Caché.
* Procesamiento asíncrono.
* Colas.
* Reintentos controlados.

---

# 20. Seguridad

La aplicación debe cumplir como mínimo:

* API Key mediante variables de entorno.
* `.env` incluido en `.gitignore`.
* No registrar API Keys en logs.
* Validar entradas.
* Limitar tamaño del texto recibido.
* No confiar directamente en contenido generado por IA.

---

# 21. Pruebas

Se deben probar como mínimo los siguientes escenarios.

### Caso 1 — Soporte técnico

Entrada:

```json
{
  "texto": "No puedo ingresar al sistema desde esta mañana"
}
```

Resultado esperado:

```text
categoria → Soporte técnico
area → TI
```

---

### Caso 2 — Recursos humanos

Entrada:

```json
{
  "texto": "Necesito actualizar mi información de vacaciones"
}
```

Resultado esperado:

```text
categoria → Recursos humanos
area → Recursos Humanos
```

---

### Caso 3 — Facturación

Entrada:

```json
{
  "texto": "Me cobraron dos veces la misma factura"
}
```

Resultado esperado:

```text
categoria → Facturación
area → Finanzas
```

---

### Caso 4 — Solicitud ambigua

Entrada:

```json
{
  "texto": "Necesito ayuda con algo"
}
```

El sistema no debe inventar información.

Debe utilizar valores seguros definidos por el sistema.

---

### Caso 5 — Entrada inválida

Entrada:

```json
{
  "texto": ""
}
```

Debe producir un error de validación.

---

# 22. Endpoint principal

## POST `/solicitudes`

### Request

```json
{
  "texto": "No puedo ingresar al sistema desde esta mañana"
}
```

### Response

```json
{
  "id": 1,
  "categoria": "Soporte técnico",
  "prioridad": "alta",
  "area": "TI",
  "resumen": "Usuario no puede acceder al sistema",
  "requiere_intervencion_humana": true
}
```

---

# 23. Documentación

FastAPI debe proporcionar documentación automática.

Se debe verificar:

```text
/docs
```

y:

```text
/openapi.json
```

La documentación debe permitir probar el endpoint.

---

# 24. Variables de entorno

Ejemplo:

```env
ANTHROPIC_API_KEY=
DATABASE_URL=
```

No se deben incluir valores reales en el repositorio.

Debe existir un archivo:

```text
.env.example
```

Ejemplo:

```env
ANTHROPIC_API_KEY=your_api_key_here
DATABASE_URL=sqlite:///./solicitudes.db
```

---

# 25. Git

El proyecto debe utilizar Git desde el inicio.

Primeros commits sugeridos:

```text
chore: initialize project
feat: add FastAPI application
feat: add request schemas
feat: integrate Claude API
feat: add request classification
feat: add database persistence
test: add classification tests
docs: add project documentation
```

---

# 26. Criterios de aceptación

El proyecto se considera terminado cuando:

* [ ] La aplicación inicia correctamente.
* [ ] `POST /solicitudes` funciona.
* [ ] Pydantic valida la entrada.
* [ ] Claude analiza la solicitud.
* [ ] La respuesta de Claude es validada.
* [ ] Las categorías están restringidas.
* [ ] Las prioridades están restringidas.
* [ ] Las áreas están restringidas.
* [ ] Las solicitudes se almacenan.
* [ ] Los errores son manejados.
* [ ] La API Key no está en el código.
* [ ] `.env` está excluido de Git.
* [ ] Existe `.env.example`.
* [ ] Existen pruebas.
* [ ] Existe README.
* [ ] Existe documentación de API.
* [ ] El endpoint puede probarse desde Postman.

---

# 27. Restricciones técnicas

Claude Code debe respetar las siguientes reglas durante la implementación:

1. No introducir dependencias innecesarias.
2. No colocar secretos en el código.
3. No utilizar respuestas de IA sin validación.
4. No modificar la arquitectura sin justificarlo.
5. Mantener separación de responsabilidades.
6. No implementar funcionalidades fuera del alcance.
7. Crear pruebas para la lógica importante.
8. Mantener código legible y mantenible.
9. Documentar decisiones técnicas relevantes.
10. Ejecutar las pruebas antes de considerar terminada una funcionalidad.

---

# 28. Preguntas técnicas que debo poder responder

Al finalizar el proyecto debo poder explicar:

### ¿Por qué utilizar IA?

Porque las solicitudes están escritas en lenguaje natural y pueden expresar la misma intención de múltiples formas.

Ejemplo:

```text
"No me deja entrar"
"El sistema no acepta mi contraseña"
"No puedo acceder a mi cuenta"
```

Un sistema basado exclusivamente en palabras clave puede requerir muchas reglas.

---

### ¿Cuándo NO utilizar IA?

Cuando una regla determinista sea suficiente.

Ejemplo:

```text
Si monto > 1.000.000
    → requiere aprobación
```

No tiene sentido pagar una llamada a un LLM para una regla matemática simple.

---

### ¿Cómo validar una respuesta de un LLM?

Mediante un esquema estructurado y validación con Pydantic.

```text
LLM
 ↓
JSON
 ↓
Pydantic
 ↓
Respuesta válida
```

---

### ¿Cómo evitar depender de texto libre?

Utilizando valores controlados:

```text
categoria ∈ categorías permitidas

prioridad ∈ prioridades permitidas

area ∈ áreas permitidas
```

---

### ¿Cómo controlar costos?

Reduciendo:

* Tokens.
* Número de llamadas.
* Tamaño de prompts.
* Información innecesaria.
* Procesamiento duplicado.

Y utilizando modelos apropiados para cada tarea.

---

### ¿Cómo controlar latencia?

Reduciendo llamadas innecesarias y diseñando la arquitectura para permitir posteriormente:

* Async.
* Caché.
* Colas.
* Procesamiento en background.

---

# 29. Evolución futura

Este proyecto debe poder evolucionar hacia una plataforma de automatización.

### Fase 1

```text
API
 ↓
Claude
 ↓
Clasificación
```

### Fase 2

```text
WhatsApp
 ↓
Webhook
 ↓
FastAPI
 ↓
Claude
 ↓
Clasificación
 ↓
Respuesta automática
```

### Fase 3

```text
WhatsApp
Email
Web
    ↓
API Gateway
    ↓
Agente IA
    ↓
Clasificación
    ↓
Base de conocimiento
    ↓
Sistemas empresariales
    ↓
Respuesta
```

El diseño actual debe evitar bloquear estas futuras extensiones.

---

# 30. Definición de terminado

El proyecto estará terminado cuando pueda demostrar, desde Postman:

```text
POST /solicitudes
        ↓
FastAPI
        ↓
Claude
        ↓
Respuesta estructurada
        ↓
Pydantic
        ↓
SQLite
        ↓
JSON
```

y explicar técnicamente **por qué cada componente existe, qué problema resuelve y cuáles son sus limitaciones**.
# 31. Uso obligatorio de Context7

Context7 debe utilizarse como fuente de documentación técnica actualizada cuando el desarrollo dependa de librerías, frameworks, SDKs, APIs o tecnologías que puedan haber cambiado.

El objetivo es evitar implementar soluciones basadas en documentación obsoleta, APIs deprecated, patrones antiguos o ejemplos incompatibles con las versiones actuales.

---

## 31.1 Regla general

Antes de implementar una funcionalidad que dependa de una tecnología externa, Claude Code debe determinar si necesita consultar Context7.

Cuando exista documentación disponible en Context7 para la tecnología utilizada, debe preferirse dicha documentación para verificar:

* APIs actuales.
* Métodos disponibles.
* Sintaxis vigente.
* Configuración actual.
* Parámetros.
* Ejemplos de código.
* Patrones recomendados.
* Cambios entre versiones.
* Funcionalidades deprecated.
* Limitaciones conocidas.
* Integraciones oficiales.

---

## 31.2 Tecnologías que deben verificarse

Para este proyecto se debe considerar especialmente Context7 para:

* Python.
* FastAPI.
* Pydantic.
* Anthropic SDK.
* Claude API.
* SQLAlchemy.
* SQLite.
* MySQL.
* Postman, cuando corresponda.
* Cualquier librería adicional que se incorpore durante el desarrollo.

Si durante la implementación aparece una nueva dependencia, también debe evaluarse la necesidad de consultar Context7.

---

## 31.3 Arquitectura

Context7 debe utilizarse para verificar que las decisiones de implementación sean compatibles con las prácticas actuales de las tecnologías utilizadas.

Antes de adoptar patrones arquitectónicos específicos, verificar cuando sea necesario:

* Estructura recomendada de FastAPI.
* Dependency Injection.
* Organización de routers.
* Servicios.
* Manejo de configuración.
* Integración con bases de datos.
* Manejo de errores.
* Procesamiento asíncrono.
* Integración con APIs externas.
* Testing.

Context7 no debe utilizarse para reemplazar el razonamiento arquitectónico.

Debe utilizarse como fuente de información técnica actualizada para tomar mejores decisiones.

---

## 31.4 APIs y SDKs

Cuando se utilice un SDK o API externa, se debe verificar mediante Context7:

1. Cómo instalar la versión actual.
2. Cómo inicializar el cliente.
3. Cómo realizar las llamadas.
4. Cómo manejar errores.
5. Cómo estructurar las respuestas.
6. Qué métodos están actualmente soportados.
7. Qué métodos están deprecated.
8. Qué parámetros son obligatorios.
9. Qué parámetros son opcionales.
10. Qué mecanismos oficiales existen para respuestas estructuradas.

Esto es especialmente importante para la integración con Claude API.

---

## 31.5 Documentación actualizada

Cuando exista riesgo de que el conocimiento utilizado pueda estar desactualizado, Claude Code debe consultar Context7 antes de implementar.

Ejemplos:

```text
FastAPI
Pydantic
Anthropic Python SDK
SQLAlchemy
```

No se debe asumir que una implementación encontrada en conocimiento previo sigue siendo válida.

---

## 31.6 Ejemplos de código

Context7 debe utilizarse para obtener ejemplos actualizados cuando sea necesario.

Los ejemplos deben utilizarse como referencia y posteriormente adaptarse a la arquitectura del proyecto.

No se debe copiar código de ejemplo sin analizar:

* Compatibilidad de versiones.
* Seguridad.
* Arquitectura.
* Manejo de errores.
* Mantenibilidad.
* Requisitos específicos del proyecto.

---

## 31.7 Seguridad

Context7 debe utilizarse cuando sea necesario para verificar las prácticas actuales de seguridad relacionadas con las tecnologías utilizadas.

Se debe investigar especialmente:

* Gestión de API Keys.
* Variables de entorno.
* Manejo de secretos.
* Validación de entradas.
* Seguridad de APIs.
* Manejo de errores.
* Logging.
* Protección de información sensible.
* Configuración segura.
* Integración segura con servicios externos.

La documentación oficial y actualizada debe tener prioridad frente a ejemplos antiguos encontrados en internet o conocimiento previo.

---

## 31.8 Casos de uso empresariales

Cuando sea relevante, Context7 debe utilizarse para investigar cómo una tecnología recomienda resolver escenarios empresariales reales.

Ejemplos:

* Integración de APIs externas.
* Procesamiento de solicitudes.
* Validación de respuestas de IA.
* Manejo de errores.
* Retries.
* Rate limiting.
* Observabilidad.
* Persistencia.
* Escalabilidad.
* Procesamiento asíncrono.

El objetivo es que la solución no sea solamente un ejercicio académico, sino que siga patrones que puedan evolucionar hacia un sistema empresarial.

---

## 31.9 Versiones y compatibilidad

Antes de agregar o actualizar una dependencia importante, verificar:

```text
Tecnología
    ↓
Versión utilizada
    ↓
Compatibilidad
    ↓
Documentación actual
    ↓
Implementación
```

No se deben utilizar APIs marcadas como deprecated cuando exista una alternativa recomendada y compatible.

Cuando exista una diferencia importante entre versiones, documentar la decisión.

---

## 31.10 Cambios de versión

Si Context7 muestra que una API, método o patrón cambió entre versiones, se debe utilizar la implementación correspondiente a la versión seleccionada para el proyecto.

Ejemplo conceptual:

```text
Versión antigua
      ↓
Método deprecated
      ↓
NO utilizar
      │
      ▼
Versión actual
      ↓
API recomendada
      ↓
UTILIZAR
```

---

## 31.11 Context7 no es opcional cuando existe riesgo técnico

Claude Code debe consultar Context7 especialmente cuando:

* No conoce con certeza la API actual.
* Existe posibilidad de breaking changes.
* Se está integrando un SDK.
* Se está configurando una tecnología.
* Se está implementando seguridad.
* Se está utilizando una funcionalidad nueva.
* Se está utilizando una funcionalidad que cambia frecuentemente.
* Existe documentación de varias versiones.
* Se encuentra un error posiblemente relacionado con una versión.
* Se necesita confirmar una API antes de implementarla.
* Se necesita verificar una práctica recomendada.

---

## 31.12 Prioridad de fuentes

Para decisiones técnicas relacionadas con una librería o framework se seguirá esta prioridad:

```text
1. Documentación oficial actual
           ↓
2. Context7 / documentación indexada actualizada
           ↓
3. Repositorio oficial
           ↓
4. Fuentes técnicas confiables
           ↓
5. Conocimiento previo del modelo
```

El conocimiento previo del modelo **no debe utilizarse como fuente definitiva** cuando la tecnología puede haber cambiado.

---

## 31.13 Registro de decisiones

Cuando una consulta a Context7 determine una decisión técnica importante, se debe registrar brevemente la decisión.

Ejemplo:

```text
Decisión:
Utilizar X para implementar Y.

Motivo:
La documentación actual recomienda X para la versión utilizada.

Alternativa descartada:
Z porque corresponde a una API deprecated.
```

No es necesario registrar cada consulta trivial.

---

## 31.14 Regla para nuevas tecnologías

Cada vez que se agregue una nueva tecnología o dependencia al proyecto:

```text
¿Es una tecnología externa?
        │
       Sí
        ↓
¿Puede haber cambiado su API?
        │
    ┌───┴───┐
   Sí       No
    ↓        ↓
Context7   Evaluar
    ↓
Verificar versión
    ↓
Verificar documentación
    ↓
Implementar
```

---

## 31.15 Objetivo final

El uso de Context7 debe garantizar que el proyecto:

* Utilice APIs actuales.
* Evite funcionalidades deprecated.
* Utilice versiones compatibles.
* Utilice patrones modernos.
* Tenga documentación técnica actualizada.
* Implemente integraciones correctamente.
* Considere prácticas empresariales.
* Considere seguridad desde el diseño.
* Reduzca errores causados por información obsoleta.
