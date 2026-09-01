# Tarea #173 — T5.3 Tracing OpenTelemetry (fase 2)

## 2026-08-30 16:45 — Completada ✅

- **Rama:** `feat/173-otel-tracing`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #173`)
- **Spec/ADR:** SPEC-019, Épica E5. Criterio vinculante: **AC3**.
- **Dependencias:** T5.1 (correlación), mergeada. La spec la marcaba como fase 2.

### Qué aporta sobre lo que ya había

Los logs de T5.1 cuentan **qué** pasó y las métricas de T5.2 **cuánto**, pero
ninguno dice **dónde se fue el tiempo** dentro de una ejecución concreta. Una traza
sí: enseña el árbol con la duración de cada rama, que es la pregunta real cuando
una generación tarda ocho minutos.

```
spans generados: 3
  agent.investigador     padre=pipeline.run   estado=UNSET request_id=corr-traza-1
  agent.redactor         padre=pipeline.run   estado=ERROR request_id=corr-traza-1
  pipeline.run           padre=(raíz)         estado=UNSET request_id=corr-traza-1
misma traza: True
```

`app/platform/tracing.py`, más un span por petición HTTP, uno raíz por ejecución
(`pipeline.run`) y uno por paso de agente colgando de él.

### Decisiones documentadas

- **Apagado significa apagado.** Sin `OTEL_ENABLED` **no se importa el SDK**, no se
  crean spans y `span()` es un `yield None`: el coste es una comprobación booleana.
  Los sitios instrumentados no comprueban nada, así que el código se lee igual en
  ambos casos. Es deliberado: el tracing exporta a un colector externo y no debe
  encenderse por accidente.
- **Nombres estándar de OTel** (`OTEL_ENABLED`, `OTEL_SERVICE_NAME`,
  `OTEL_EXPORTER_OTLP_ENDPOINT`) para que quien ya opera un colector reconozca las
  variables sin traducir nada.
- **`BatchSpanProcessor`, no `Simple`.** El simple bloquea la petición hasta que el
  colector responde: un colector lento se convertiría en latencia del usuario.
- **Se integra con lo que ya existe** en vez de duplicarlo: cada span lleva el
  `request_id` de T5.1, así que desde una traza se llega al log exacto y al revés.
- **El span de petición se nombra con la plantilla de ruta**, igual que la etiqueta
  de las métricas: un nombre por artículo haría ilegible cualquier agrupación en el
  visor de trazas.
- **Encender sin endpoint avisa** en vez de fallar: se generan spans que no van a
  ningún sitio, y eso es un fallo silencioso de configuración que conviene ver.
- **Un fallo al inicializar degrada, no tumba el arranque.** Como con Redis en
  T4.3: perder observabilidad empeora el diagnóstico, no arrancar deja el servicio
  fuera del todo.
- **Las dependencias van en el lock aunque el uso sea opcional**: encender el
  tracing en producción no debe exigir un segundo camino de instalación. Son 6
  paquetes de los 89 del lock.

### Dos problemas de test que valían la pena entender

**El proveedor global de OTel solo se puede fijar una vez por proceso**
(`Overriding of current TracerProvider is not allowed`). Con un fixture que llamaba
a `set_tracer_provider` por test, a partir del segundo los spans se iban al
exportador del primero y los casos se contaminaban. Se resuelve usando un proveedor
**local** y sacando el tracer de él.

**Importar `app.main` ejecuta `setup_tracing()`**, que deja `_tracer` a `None` — y
borraba el parche del fixture cuando el import ocurría después. El fixture importa
la app **antes** de parchear. El síntoma era engañoso: un test pasaba y el otro no,
según el orden.

### Test nuevo

`backend/tests/test_tracing.py` (17 casos), capturando spans con
`InMemorySpanExporter` para comprobar **el árbol de verdad** —padres, hijos y
atributos— en lugar de dar por bueno que se llamó a la librería:
- **Apagado por defecto**: el valor de fábrica es `False`; `setup_tracing` no hace
  nada; `span()` no crea nada y `record_error(None, …)` no lanza; una
  inicialización rota degrada sin tumbar el arranque.
- **Anidamiento**: los spans de agente cuelgan del de pipeline; todos comparten
  traza; los atributos se registran y los `None` **se omiten** en vez de guardarse
  como `"None"`, que sería ruido en las búsquedas; un paso fallido se marca
  `ERROR` con su excepción —sin marcarlo, la traza saldría verde y mentiría—.
- **Correlación**: los spans llevan el `request_id`, y sin él el atributo no
  aparece.
- **Peticiones**: cada una genera su span con el código de estado, y el nombre usa
  la plantilla de ruta, no el UUID.
- **Configuración**: nombres estándar, aviso al encender sin endpoint,
  dependencias pineadas y `otel.enabled: false` en los dos `config.yaml`.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_tracing.py -q
# → 17 passed
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 575 passed
python scripts/validate_specs.py   # → [OK]
```

El lock se recompiló y se verificó en un venv limpio de Python 3.12: **575 passed**
con las versiones exactas.

### Definition of Done (AC3)

- [x] **AC3** — con el tracing habilitado, cada petición y cada paso de agente
  generan spans anidados exportables por OTLP; apagado por defecto.
- [x] Tests que cubren el cambio, en verde (17 nuevos; 575 en la suite).
- [x] Docs: **AC3 marcado en SPEC-019**; sección `otel` en los dos `config.yaml`.
- [x] Sin secretos en el diff; dependencias nuevas pineadas con hash.
- [x] Rama con prefijo `feat/` hacia `develop`.

### Cierre de la épica E5

Con T5.3, **E5 (Observabilidad) queda completa** y los **cuatro** criterios de
SPEC-019 están marcados: logging estructurado con correlación (T5.1), métricas
Prometheus (T5.2), tracing OTel (T5.3) y liveness/readiness (T5.4).

### Seguimiento

- **No se añade un colector al compose.** Depende de qué use cada despliegue
  (Jaeger, Tempo, un colector OTel genérico), y levantar uno que nadie mire sería
  ruido. Basta con apuntar `OTEL_EXPORTER_OTLP_ENDPOINT` al que ya haya.
- El span del pipeline **no se propaga entre workers**: una ejecución vive entera
  en un worker (T4.3), así que su traza también. Si algún día el pipeline se
  repartiera, habría que propagar el contexto por el bus.
