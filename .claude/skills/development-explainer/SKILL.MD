---

name: development-explainer
description: Explica de forma clara y resumida qué está haciendo Claude durante el desarrollo, por qué lo hace, qué resultado obtuvo y registra las decisiones importantes del proyecto. Debe utilizarse durante implementación, depuración, investigación técnica, consultas a Context7, cambios arquitectónicos, instalación de dependencias, pruebas y resolución de errores.
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Development Explainer

## Objetivo

Actuar como una capa de explicación pedagógica durante el desarrollo del proyecto.

El usuario debe poder comprender, sin necesidad de revisar todo el código, qué está haciendo Claude, por qué lo está haciendo y cuál fue el resultado.

La explicación debe ser técnica pero comprensible.

No explicar cada línea de código.

Explicar principalmente:

* Decisiones técnicas.
* Cambios importantes.
* Arquitectura.
* Integraciones.
* Dependencias.
* Uso de APIs.
* Consultas a Context7.
* Seguridad.
* Errores.
* Pruebas.
* Resultados.
* Decisiones descartadas.

---

# 1. Explicación en consola

Antes o después de cada operación importante, mostrar una explicación breve.

Utilizar preferentemente este formato:

```text
[FASE]

Qué hago:
Descripción breve de la acción.

Por qué:
Razón técnica de la acción.

Resultado:
Resultado obtenido o siguiente paso.
```

Ejemplo:

```text
[FASE 2 — Integración con Claude]

Qué hago:
Voy a crear el servicio encargado de comunicarse con Claude API.

Por qué:
La integración con el proveedor de IA debe estar separada de
los endpoints para mantener una arquitectura modular.

Resultado:
La comunicación con Claude quedará encapsulada en `ia_service.py`.
```

---

# 2. Mantener las explicaciones resumidas

Las explicaciones deben ser suficientemente claras para que el usuario entienda el proceso, pero no deben convertirse en una narración excesiva.

Evitar:

```text
Ahora voy a abrir este archivo...
Ahora voy a mover esta línea...
Ahora voy a escribir esta función...
```

Preferir:

```text
[FASE — Separación de responsabilidades]

Qué hago:
Voy a separar la lógica de IA del endpoint.

Por qué:
El endpoint debe encargarse de HTTP y el servicio debe encargarse
de la comunicación con Claude.

Resultado:
La lógica queda desacoplada y será más fácil de probar.
```

---

# 3. Antes de modificar código

Cuando una tarea sea importante, explicar primero el plan.

Ejemplo:

```text
[PLAN]

1. Revisar la estructura actual.
2. Verificar la documentación necesaria mediante Context7.
3. Implementar el cambio.
4. Ejecutar pruebas.
5. Revisar el resultado.
```

No realizar cambios arquitectónicos importantes sin explicar previamente el motivo.

---

# 4. Uso de Context7

Cuando sea necesario consultar Context7, informarlo al usuario.

Utilizar este formato:

```text
[INVESTIGACIÓN — Context7]

Tecnología:
FastAPI

Qué verifico:
API y patrón recomendado para la versión utilizada.

Por qué:
Quiero evitar implementar utilizando documentación obsoleta.

Resultado:
Se utilizará la API/patrón recomendado actualmente.
```

Si la consulta a Context7 cambia una decisión técnica, explicarlo.

Ejemplo:

```text
[DECISIÓN TÉCNICA]

Context7 mostró que el enfoque utilizado anteriormente está
deprecated en la versión actual.

Decisión:
Utilizar la API recomendada actualmente.

Motivo:
Evitar implementar sobre una API obsoleta.
```

---

# 5. Instalación de dependencias

Antes de agregar una dependencia importante:

```text
[DEPENDENCIA]

Dependencia:
nombre-paquete

Por qué:
Problema que resuelve.

Necesidad:
Por qué no se puede resolver razonablemente con las dependencias
existentes.

Verificación:
Se verificó compatibilidad con la versión utilizada.
```

No agregar dependencias innecesarias.

---

# 6. Cambios arquitectónicos

Cuando se modifique la arquitectura:

```text
[ARQUITECTURA]

Cambio:
Descripción.

Problema:
Qué problema resuelve.

Motivo:
Por qué esta solución es apropiada.

Impacto:
Qué componentes afecta.

Resultado:
Cómo queda la arquitectura.
```

Ejemplo:

```text
[ARQUITECTURA]

Cambio:
Separamos la comunicación con Claude en `ia_service.py`.

Problema:
El endpoint estaba mezclando HTTP y lógica de IA.

Motivo:
Separar responsabilidades.

Impacto:
El endpoint queda más simple y el servicio puede probarse
independientemente.

Resultado:
API → Service → Claude API.
```

---

# 7. Seguridad

Cuando se implemente o modifique un componente relacionado con seguridad, explicarlo.

Ejemplo:

```text
[SEGURIDAD]

Qué hago:
Mover la API Key a una variable de entorno.

Por qué:
Las credenciales no deben almacenarse en el código fuente.

Resultado:
La API Key queda fuera del repositorio.
```

Prestar especial atención a:

* API Keys.
* Tokens.
* Contraseñas.
* Variables de entorno.
* Logs.
* Información sensible.
* Validación de entrada.
* Errores expuestos al cliente.

Nunca mostrar secretos en la consola ni en `DEVELOPMENT_LOG.md`.

---

# 8. Errores

Cuando aparezca un error importante, no ocultarlo.

Explicarlo de forma resumida:

```text
[ERROR]

Problema:
Descripción del error.

Causa:
Causa identificada.

Solución:
Qué se modificará.

Resultado:
Resultado después de aplicar la solución.
```

Ejemplo:

```text
[ERROR]

Problema:
La respuesta de Claude no cumple el esquema esperado.

Causa:
El modelo devolvió un valor fuera de las categorías permitidas.

Solución:
Se agregará validación mediante Pydantic.

Resultado:
Las respuestas inválidas no serán almacenadas.
```

---

# 9. Pruebas

Después de implementar una funcionalidad importante, informar las pruebas.

```text
[PRUEBAS]

Qué se probó:
POST /solicitudes

Casos:
- Solicitud válida.
- Solicitud vacía.
- Solicitud ambigua.
- Respuesta inválida de IA.

Resultado:
4/4 pruebas correctas.
```

No afirmar que una prueba pasó si realmente no fue ejecutada.

---

# 10. Registro permanente

Las decisiones importantes deben registrarse en:

```text
docs/process/DEVELOPMENT_LOG.md
```

El registro debe ser conciso.

Formato:

```markdown
## YYYY-MM-DD — Nombre de la fase

### Qué se hizo

Descripción.

### Por qué

Motivo.

### Decisión

Decisión técnica tomada.

### Resultado

Resultado obtenido.

### Context7

Indicar si se consultó y qué decisión ayudó a tomar.
```

No registrar información sensible.

No registrar cada modificación trivial.

---

# 11. Cuándo registrar

Registrar especialmente:

* Inicio de una fase importante.
* Cambios arquitectónicos.
* Nuevas dependencias.
* Integraciones externas.
* Decisiones de seguridad.
* Cambios de base de datos.
* Cambios de API.
* Problemas importantes.
* Soluciones de errores.
* Decisiones tomadas después de consultar Context7.
* Cambios que puedan afectar futuras funcionalidades.

---

# 12. Cuándo NO registrar

No es necesario registrar:

* Cambios triviales de formato.
* Correcciones menores de espacios.
* Renombrados internos sin impacto.
* Ediciones que no cambian comportamiento.
* Cada comando ejecutado individualmente.

El objetivo es conservar el conocimiento importante del desarrollo.

---

# 13. Finalización de una tarea

Al terminar una tarea importante, mostrar:

```text
[COMPLETADO]

Qué se hizo:
...

Archivos principales afectados:
...

Pruebas:
...

Resultado:
...

Siguiente paso:
...
```

Ejemplo:

```text
[COMPLETADO]

Qué se hizo:
Se implementó el endpoint POST /solicitudes.

Archivos principales:
- app/api/routes/solicitudes.py
- app/services/solicitud_service.py
- app/schemas/solicitud.py

Pruebas:
Endpoint probado correctamente.

Resultado:
La solicitud puede recibirse, clasificarse y validarse.

Siguiente paso:
Implementar persistencia en SQLite.
```

---

# 14. Comportamiento pedagógico

El usuario está utilizando el proyecto también como ejercicio de aprendizaje.

Por lo tanto, cuando una decisión técnica sea relevante, explicar brevemente el concepto.

Ejemplo:

```text
¿Por qué Pydantic?

Pydantic permite validar que los datos recibidos y generados
cumplan un esquema definido antes de utilizarlos.
```

No convertir cada acción en una clase teórica.

Explicar únicamente aquello que ayude a comprender la decisión.

---

# 15. Regla de transparencia

Nunca afirmar:

* "Consulté Context7" si no fue consultado.
* "La documentación recomienda..." sin haberlo verificado.
* "Las pruebas pasaron" si no fueron ejecutadas.
* "La implementación es segura" sin haber realizado una revisión.
* "La API está actualizada" sin verificar la versión correspondiente.

Las explicaciones deben reflejar lo que realmente ocurrió.

---

# 16. Regla principal

El objetivo de esta skill no es generar más texto.

El objetivo es hacer visible el razonamiento práctico del desarrollo:

```text
Qué hago
    ↓
Por qué
    ↓
Cómo lo implemento
    ↓
Cómo lo verifico
    ↓
Qué resultado obtuve
```

Las explicaciones deben ser:

* Breves.
* Técnicas.
* Claras.
* Verificables.
* Pedagógicas.
* Orientadas a decisiones.
