# Política de retención de datos y PII

- **Estado:** vigente
- **Spec:** [SPEC-020](../specs/SPEC-020-governance-supply-chain.md) — **AC5**
- **Épica:** E6 (Gobernanza y Calidad)
- **Última revisión:** 2026-08-30

Qué guarda la plataforma, cuánto tiempo y cómo se purga. Las ventanas viven en
`backend/app/core/config.py` (`RETENTION_*`) y se aplican con
`python -m app.platform.retention`.

> Este documento y esa configuración tienen que ir juntos. Cambiar una ventana sin
> actualizar aquí deja la política mintiendo, que es peor que no tenerla.

## 1. Qué se guarda

### 1.1 Contenido y configuración — **no caduca**

| Conjunto | Contiene | PII |
|---|---|---|
| `users` | correo, nombre, hash de contraseña, rol | **Sí** |
| `projects`, `agent_profiles`, `saved_flows` | configuración de la plataforma | No |
| `articles` | título, cuerpo, resumen, autores, HTML maquetado | Nombres de autor |
| `user_project_access` | qué usuario accede a qué proyecto | Referencia |
| Figuras (`backend/app/.assets/`) | imágenes subidas a los artículos | Posible |

**No se purgan por antigüedad, y es deliberado.** Son el producto, no su rastro:
borrarlos por edad destruiría el trabajo de alguien. Se eliminan por decisión
explícita de su propietario, no por un proceso automático.

### 1.2 Registro y rastro — **caduca**

| Conjunto | Contiene | PII | Ventana | Ajuste |
|---|---|---|---|---|
| `audit_log` | actor, acción, objetivo, **IP**, correo enmascarado | **Sí** (IP) | **365 días** | `RETENTION_AUDIT_LOG_DAYS` |
| `agent_runs` | entrada y salida de cada ejecución del pipeline | Posible | **90 días** | `RETENTION_AGENT_RUNS_DAYS` |
| `flow_checkpoints` | estado intermedio para reanudar un pipeline | Posible | **30 días** | `RETENTION_CHECKPOINTS_DAYS` |
| `notifications` (leídas) | avisos en la aplicación | Referencia | **90 días** | `RETENTION_NOTIFICATIONS_DAYS` |
| Figuras huérfanas | imágenes que ningún artículo referencia | Posible | **30 días** | `RETENTION_ORPHAN_ASSETS_DAYS` |

Por qué esas ventanas:

- **`audit_log`, 365 días.** Es evidencia de seguridad: una investigación de
  incidente suele mirar meses atrás, y la IP es el dato que lo hace útil. Un año es
  el equilibrio habitual entre poder investigar y no acumular direcciones IP
  indefinidamente.
- **`agent_runs`, 90 días.** Guarda literalmente lo que el usuario escribió y lo que
  el modelo respondió. Es lo más sensible que hay fuera de `users`, y su valor
  —depurar una ejecución, revisar consumo— se agota en semanas.
- **`flow_checkpoints`, 30 días.** Son puntos de reanudación. Un checkpoint de hace
  un mes ya no se va a reanudar; solo ocupa y conserva borradores.
- **`notifications`, 90 días, solo las leídas.** Una notificación **sin leer** sigue
  pendiente de alguien por vieja que sea, así que nunca caduca.
- **Figuras huérfanas, 30 días.** Una figura recién subida todavía no aparece en
  ningún cuerpo —el usuario aún no ha pegado la referencia—, así que purgar por
  «huérfana» sin margen borraría justo lo que se acaba de subir.

### 1.3 Logs de aplicación

Los logs estructurados (SPEC-019/T5.1) salen por `stdout` y **no los retiene la
aplicación**: su ciclo de vida es el del recolector de logs del despliegue. Llevan
`request_id`, correos **enmascarados** e IPs. Configurar ahí una retención
equivalente a la del `audit_log` es responsabilidad del operador; la aplicación no
puede imponerla.

## 2. Minimización aplicada

Decisiones ya tomadas en el código, no aspiraciones:

- **Los correos se enmascaran** (`a***@dominio.com`) tanto en los logs de auth como
  en el `audit_log`. En un intento de login fallido lo único disponible es el correo
  **tecleado**, que puede ni existir: guardarlo entero convertiría la tabla en un
  listado de direcciones.
- **El `audit_log` no tiene clave ajena a `users`**: guarda el UUID del actor, que
  identifica sin arrastrar datos personales.
- **No se guarda nunca la contraseña intentada**, ni siquiera enmascarada.
- **Las claves de API no se versionan ni se exponen**: `ANTHROPIC_API_KEY` se
  inyecta por entorno y la interfaz solo informa de si está presente.

## 3. Cómo se purga

```bash
cd backend
python -m app.platform.retention            # simula: cuenta y no borra nada
python -m app.platform.retention --apply    # ejecuta la purga
```

**La simulación es el modo por defecto** a propósito: una purga es irreversible y se
ejecuta sobre producción, así que el comando corto tiene que ser el que no destruye.

Para **conservar** un conjunto —una obligación legal, una investigación abierta— se
pone su ventana a `0`, que desactiva su purga; el informe lo indica explícitamente
en lugar de callarlo.

Ejemplo (`backend/config.yaml`, o por variable de entorno):

```yaml
retention:
  audit_log_days: 365
  agent_runs_days: 90
  checkpoints_days: 30
  notifications_days: 90
  orphan_assets_days: 30
```

No hay endpoint HTTP de purga, y no es un olvido: borrar en masa no debe estar a
una llamada de distancia. El `audit_log` es además **solo de lectura** por API.

### Programarla

La purga no se ejecuta sola. Conviene lanzarla periódicamente —cron diario o
semanal en el entorno de despliegue— **empezando en modo simulación** hasta ver
volúmenes razonables en el informe.

## 4. Lo que esta política todavía no cubre

Dicho explícitamente, para que no se confunda con estar resuelto:

- **Derecho de supresión de una persona concreta.** No hay un «borra todo lo de este
  usuario». Requiere decisiones de producto que no corresponden a esta tarea: qué
  pasa con los artículos que escribió, con las publicaciones ya hechas y con las
  entradas de auditoría que le nombran (borrarlas destruiría el rastro que justifica
  tener auditoría).
- **Vectores en Qdrant.** Los documentos indexados para RAG se borran uno a uno
  desde la aplicación —y ese borrado **sí** queda auditado (T6.4)—, pero no caducan
  por antigüedad.
- **Copias de seguridad.** Purgar la base no purga sus backups. Alinear ambas
  retenciones es responsabilidad del operador.
- **Retención de los logs de aplicación**, por lo dicho en §1.3.
