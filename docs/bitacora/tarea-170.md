# Tarea #170 — T4.3 Externalizar el estado en memoria a Redis (multi-worker)

## 2026-08-30 15:00 — Completada ✅

- **Rama:** `feat/170-redis-multiworker`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #170`)
- **Spec/ADR:** SPEC-018, Épica E4. Criterio vinculante: **AC3**.
- **Dependencias:** **T3.2**, cerrada al completarse E3. Estaba bloqueada hasta
  entonces.

### El problema

Tres registros vivían en diccionarios del proceso: `active_streams`,
`active_tasks` y `pending_decisions`. Con **un** worker da igual —quien ejecuta el
pipeline, quien atiende el SSE y quien recibe la decisión son el mismo—. Con
**varios**, cada cosa cae en un proceso distinto:

- el navegador se conecta al worker B mientras el pipeline corre en el A, y **no ve
  un solo evento**;
- la decisión humana llega al C, que no tiene el `Future` que espera nadie;
- y el ticket de stream lo emite un worker y lo canjea otro, que no lo reconoce:
  `403` sin motivo aparente.

### Qué se hizo

**`app/platform/bus.py`**, con dos implementaciones tras una misma interfaz:
`InProcessBus` (lo que había, sin cambios de comportamiento) y `RedisBus`
(pub/sub). El backend se elige con `REDIS_ENABLED`.

Migran al bus: eventos SSE, presencia del pipeline, señal de cancelación, decisión
humana y **el almacén de tickets** (SPEC-015/AC3), como pedía el diseño de la spec.

### Decisiones documentadas

- **Hace falta un interruptor propio, no «¿hay `REDIS_URL`?».** Esa variable tiene
  un valor por defecto **no vacío**, así que «sin configurar» es indistinguible de
  «configurado» y el fallback que pide la spec no se activaría nunca. De ahí
  `REDIS_ENABLED`, apagado por defecto: desarrollar no debe exigir levantar Redis.
- **La tarea no viaja; la señal sí.** `active_tasks` guarda objetos `asyncio.Task`:
  manejadores de corrutinas vivas, no datos serializables. Se queda **local al
  worker**, y cancelar publica un mensaje de control que el worker dueño atiende.
  Igual con la decisión: el `Future` vive donde espera el pipeline y por el bus solo
  va el valor. Por eso `RedisBus` **hereda** de `InProcessBus`: deja explícito qué
  parte sigue siendo local y cuál se comparte.
- **`mark_running`/`is_running`.** Sin presencia compartida, un `409 No active
  pipeline` sería mentira en cuanto el pipeline corriese en otro worker. Las claves
  llevan TTL: si un worker muere a mitad, caducan solas en vez de bloquear el
  artículo para siempre.
- **`publish_event` sigue siendo síncrona.** Los agentes emiten tokens y logs desde
  *callbacks* que no pueden hacer `await`. Con Redis se encola en un buzón que
  vacía **una sola** tarea, en orden: lanzar una tarea por evento habría barajado
  los `token`, y eso es peor que llegar tarde, porque el cliente compone el texto en
  el orden de llegada. Hay test.
- **`GETDEL` para los tickets.** Es lo que mantiene cierto el «un solo uso» con
  varios workers: un `GET` seguido de `DELETE` deja una ventana en la que dos
  conexiones simultáneas canjearían el mismo ticket.
- **Un Redis roto degrada, no tumba el arranque.** Se avisa por log y se cae al bus
  en proceso: perder la coordinación empeora el servicio, no arrancar lo deja fuera
  del todo.
- **Redis sin persistencia** en el compose (`--save "" --appendonly no`): aquí solo
  viven eventos en vuelo, decisiones pendientes y tickets de segundos. Nada que deba
  sobrevivir a un reinicio.

### Verificación — contra un Redis real

El entorno tenía **Redis 7.0.15**, así que AC3 se probó contra el servidor de
verdad y no contra un doble. Dos instancias del bus, con conexiones separadas y
nada en memoria en común, equivalen a dos workers:

```
evento en A: {'type': 'token', 'text': 'hola'}
evento en B: {'type': 'token', 'text': 'hola'}
B ve el pipeline en curso: True
B pide cancelar: True   →  A canceló su tarea: True
B entrega la decisión: True  →  A la recibe: add_source
sin decisión pendiente -> False
orden preservado: True
```

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_bus_multiworker.py -q
# → 36 passed   (19 de ellos específicos de Redis)
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 539 passed
python scripts/validate_specs.py   # → [OK]
```

Y **sin** Redis levantado, como en la CI: `21 passed, 15 skipped`. Los casos de
Redis se saltan solos en vez de teñir de rojo un CI que no levanta el servicio.

El lock se recompiló con la dependencia nueva y se verificó instalándolo en un venv
limpio de Python 3.12: `539 passed` con las versiones exactas.

### Test nuevo

`backend/tests/test_bus_multiworker.py` (36 casos), **cada uno contra los dos
backends**:
- **Eventos**: un suscriptor en otro worker los recibe; **dos suscriptores reciben
  los mismos** —el test que pide el plan de pruebas de la spec—; se preserva el
  orden; no se filtran eventos de otro artículo; y darse de baja corta la entrega
  (si no, cada cliente desconectado dejaría una fuga).
- **Presencia y cancelación**: otro worker ve el pipeline en curso; cancelar desde
  otro worker llega a la tarea; cancelar algo que no corre lo dice.
- **Decisión humana**: la entregada en otro worker reanuda el pipeline; sin nadie
  esperando devuelve `False` —lo que hace honesto el `409`—; y la marca desaparece
  al terminar la espera.
- **Tickets**: emitido en un worker y válido en otro; de un solo uso entre workers;
  desconocido rechazado.
- **Backend y degradación**: por defecto en proceso; con el flag, Redis; con Redis
  roto, degrada sin tumbar el arranque.
- **Despliegue**: el compose trae Redis con healthcheck y sin publicar puertos, el
  backend lo espera sano, producción enciende la coordinación, y el lock incluye la
  dependencia.

### Definition of Done (AC3)

- [x] **AC3** — streams, tareas y decisiones se coordinan vía Redis; cualquier
  worker puede atender la conexión sin pérdida de eventos.
- [x] Tests que cubren el cambio, en verde (36 nuevos; 539 en la suite).
- [x] Docs: **AC1–AC3 marcados en SPEC-018**; sección `redis` en los dos
  `config.yaml`; los porqués viven en el docstring del bus.
- [x] Sin secretos en el diff; dependencia nueva pineada con hash.
- [x] Rama con prefijo `feat/` hacia `develop`.

### Cierre de la épica E4

Con T4.3, **E4 (Datos y persistencia) queda completa**: Alembic (T4.1), `dev.db`
fuera de git (T4.2) y coordinación multi-worker (T4.3). Los tres criterios de
SPEC-018 están marcados.

### Seguimiento — lo que **todavía** no soporta varios workers

**El checkpointer de LangGraph sigue siendo por proceso** (`InMemorySaver`). El bus
comparte eventos, decisiones y tickets, pero no eso: si una **reanudación** cae en
un worker distinto del que guardó el checkpoint, no lo encuentra y el pipeline
empieza de cero. Para que `resume` funcione entre workers hace falta un saver
compartido (`langgraph-checkpoint-redis`, o el de Postgres). Queda anotado en el
propio código, junto a la definición del checkpointer.

Por eso **el compose de producción no sube todavía el número de workers de uvicorn**:
esta PR deja la coordinación lista, pero subirlo es una decisión que conviene tomar
sabiendo lo de arriba.
