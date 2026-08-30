# Tarea #179 — T6.5 Política de retención de datos y PII

## 2026-08-30 11:10 — Completada ✅

- **Rama:** `feat/179-data-retention`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #179`)
- **Spec/ADR:** SPEC-020, Épica E6. Criterio vinculante: **AC5**.
- **Dependencias:** ninguna. Llega detrás de **#178 (T6.4)** a propósito: el
  `audit_log` guarda IPs y crece sin tope, así que era una de las tablas que esta
  política tenía que cubrir desde el primer día.

### Qué se hizo

Las dos mitades que pide AC5:

**El documento** — [`docs/governance/data-retention.md`](../governance/data-retention.md):
qué se guarda, cuánto y cómo se purga, con el porqué de cada ventana. Enlazado
desde `GOVERNANCE §8` y desde `CLAUDE.md`.

**El mecanismo** — `app/platform/retention.py`, ejecutable:

```
cd backend
python -m app.platform.retention            # simula
python -m app.platform.retention --apply    # purga
```

Ventanas en `RETENTION_*` (env > `config.yaml` > defaults), documentadas también en
los dos `config.yaml`.

| Conjunto | Ventana | Por qué |
|---|---|---|
| `audit_log` | 365 días | Evidencia de seguridad; una investigación mira meses atrás, pero acumular IPs indefinidamente no |
| `agent_runs` | 90 días | Guarda lo que el usuario escribió y lo que el modelo respondió; su valor se agota en semanas |
| `flow_checkpoints` | 30 días | Puntos de reanudación: uno de hace un mes ya no se reanuda |
| `notifications` (leídas) | 90 días | — |
| Figuras huérfanas | 30 días | — |

### Decisiones documentadas

- **Solo caduca el rastro, nunca el contenido.** Usuarios, proyectos, artículos,
  perfiles y flujos **no** se purgan por antigüedad: son el producto. Borrarlos por
  edad destruiría el trabajo de alguien, y eliminarlos es una decisión de su
  propietario, no de un cron. Hay test que lo fija.
- **Simulación por defecto**, como `/sdd-sync`. Una purga es irreversible y se
  ejecuta sobre producción: el comando corto tiene que ser el que no destruye.
- **`0` desactiva una ventana** y el informe lo **dice** en vez de callarlo. Es el
  mecanismo para conservar ante una obligación legal o una investigación abierta;
  si el informe mostrara «0 purgados» sin más, no se distinguiría de «no había
  nada que purgar».
- **Las notificaciones sin leer no caducan nunca.** Siguen pendientes de alguien por
  viejas que sean; solo se purgan las ya leídas.
- **Las figuras huérfanas necesitan margen de antigüedad.** Una recién subida
  todavía no aparece en ningún cuerpo —el usuario aún no ha pegado la referencia—,
  así que purgar por «huérfana» sin margen borraría justo lo que se acaba de subir.
  Y la purga solo toca ficheros con **forma de asset**: cualquier otra cosa en el
  directorio se queda.
- **No hay endpoint HTTP de purga**, y no es un olvido: borrar en masa no debe estar
  a una llamada de distancia.
- **Los huecos se escriben.** El documento tiene una sección de lo que **no** cubre
  —derecho de supresión individual, vectores de Qdrant, copias de seguridad,
  retención de los logs de aplicación— porque una política que calla sus límites se
  lee como si no los tuviera. El derecho de supresión, en particular, exige
  decisiones de producto que no son de esta tarea: qué pasa con los artículos que
  escribió esa persona y con las entradas de auditoría que la nombran (borrarlas
  destruiría el rastro que justifica tener auditoría).

### Test nuevo

`backend/tests/test_data_retention.py` (28 casos). Dos bloques:

**La purga**: la simulación cuenta sin borrar; `--apply` borra **solo** lo pasado de
ventana; las notificaciones sin leer sobreviven; usuarios y artículos no se tocan;
ventana `0` conserva y se reporta; purgar dos veces es idempotente; el informe dice
en claro que no ha borrado nada. En figuras: la referenciada sobrevive, la huérfana
antigua cae, la recién subida se respeta y un fichero ajeno del directorio no se
toca.

**El documento contra el código**: cada conjunto que el código purga aparece en la
política con su variable, **y los números coinciden con los valores por defecto**.
Comprobado que el guardarraíl funciona: con `RETENTION_AGENT_RUNS_DAYS=45` el test
falla con `assert '45 días' in …`. Sin él, la política se quedaría desfasada al
primer ajuste, que es exactamente cómo una política deja de valer.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_data_retention.py -q
# → 28 passed
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 381 passed
python scripts/validate_specs.py   # → [OK]
```

Y el ejecutable, contra un esquema real:

```
Retención — caducarían:
  agent_runs             0
  audit_log              0
  flow_checkpoints       0
  notifications          0
  orphan_assets          0
  TOTAL                  0

Simulación: no se ha borrado nada. Ejecuta con --apply.
```

### Definition of Done (AC5)

- [x] **AC5** — política de retención documentada (qué, cuánto, cómo) y mecanismo
  de purga aplicable.
- [x] Tests que cubren el cambio, en verde (28 nuevos; 381 en la suite).
- [x] Docs: política nueva, enlazada desde `GOVERNANCE §8` y `CLAUDE.md`; sección
  `retention` en los dos `config.yaml`.
- [x] Sin secretos ni PII en el diff.
- [x] Rama con prefijo `feat/` hacia `develop`.

### Cierre de la épica E6

Con T6.5, **E6 (Gobernanza y Calidad) queda cubierta** en sus seis criterios: CI
(AC1), escaneo y Dependabot (AC2), pineado con hashes (AC3), audit log (AC4),
retención (AC5) y SDD formalizado (AC6).

Ojo con dos issues: **#175 (T6.1)** y **#180 (T6.6)** siguen **abiertos** aunque su
trabajo está hecho desde antes —`ci.yml`, `GOVERNANCE.md`, `CODEOWNERS`,
`validate_specs.py`—. Cerrarlos es decisión humana (GOVERNANCE §3.1).

### Seguimiento

- **La purga no se ejecuta sola.** Falta programarla en el entorno de despliegue
  (cron diario o semanal), empezando en modo simulación hasta ver volúmenes
  razonables. No se añade aquí porque depende del despliegue, no del repositorio.
- El **derecho de supresión individual** merece su propia tarea, con las decisiones
  de producto que implica.
