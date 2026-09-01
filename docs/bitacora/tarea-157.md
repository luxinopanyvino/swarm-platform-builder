# Tarea #157 — T1.5 `ENABLE_DEV_ROLE_PROMOTION` por defecto False + gate de producción

## 2026-08-30 13:55 — Completada ✅

- **Rama:** `sec/157-dev-role-promotion-gate`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #157`)
- **Spec/ADR:** SPEC-015, Épica E1. Criterio vinculante: **AC4**.
- **Dependencias:** ninguna. Reutiliza el mecanismo `_DEV_ONLY_FLAGS` creado en
  **#158 (T1.6)**, ya mergeado.

### Qué faltaba

AC4 tiene dos mitades y solo estaba hecha una:

| | Estado antes |
|---|---|
| El flag **ausente** ⇒ efectivo `False` | ✅ ya se cumplía (`test_secure_registration_rbac.py`) |
| Un **`config.yaml` que lo activa** con `DEBUG=false` ⇒ efectivo `False` | ❌ **no** |

Y la mitad que faltaba es justo la peligrosa: ser fail-safe *cuando el flag falta*
no cubre el caso real, porque **un `config.yaml` con el flag a `true` viaja en el
repositorio** y se despliega tal cual. El riesgo no es olvidarse de ponerlo, sino
olvidarse de quitarlo.

El endpoint que abre ese flag —`/auth/dev/promote-reviewer`— deja que un usuario se
cambie el rol a sí mismo. En producción eso es una escalada de privilegios.

Lo encontré leyendo SPEC-015 mientras resolvía #158, y lo dejé anotado allí en vez
de mezclarlo.

### Qué se hizo

Una línea de código: `ENABLE_DEV_ROLE_PROMOTION` entra en la tupla
`_DEV_ONLY_FLAGS`, con lo que su valor efectivo pasa a ser `False` con `DEBUG=false`
**venga de donde venga** —entorno o `config.yaml`—.

| `DEBUG` | configurado | efectivo |
|---|---|---|
| true | true | **True** |
| true | false | False |
| false | **true** | **False** |
| false | false | False |

El comentario de la tupla se reescribe para explicar **por qué** existe y qué abre
cada flag, de modo que quien añada uno nuevo sepa que también va ahí.

### Decisiones documentadas

- **Se cierra en la configuración, no en el endpoint.** Hay **dos** sitios que leen
  este flag —`app/routers/auth.py` y `app/modules/auth/adapters/http.py`, este
  último ni siquiera montado hoy—. Poner la comprobación en cada uno habría dejado
  la puerta abierta en el que se olvidara, y en el que se añada mañana.
- **El gate no puede convertirse en «siempre apagado»**: `dev-local.cmd` usa este
  atajo. Hay un test que comprueba que con `DEBUG=true` sigue encendiéndose, y otro
  de extremo a extremo que verifica que el endpoint **responde 200** en desarrollo.
  Sin ellos, «403 siempre» pasaría por arreglo.
- **Los `config.yaml` se dejan en `false`**, aunque ya no bastaría para activarlo:
  versionarlo a `true` sería una señal equivocada para quien lea el fichero.

### Test nuevo

`backend/tests/test_dev_role_promotion_gate.py` (14 casos):
- **AC4 / valor efectivo**: un `config.yaml` que lo activa no puede encenderlo en
  producción —el hueco— ni tampoco una variable de entorno; ausente sigue siendo
  `False`; desarrollo **sí** puede encenderlo; las cuatro combinaciones de
  `DEBUG`×configurado; y el flag está registrado como *dev-only*, para que sacarlo
  de la tupla lo diga un test antes que un incidente.
- **AC4 / endpoint**: `403` con `DEBUG=false`; **el rol no cambia** pese al `403`
  —un `403` tiene que significar «no pasó nada», no «no te lo cuento»—; y `200` en
  desarrollo.
- **Coherencia**: los dos `config.yaml` y los dos compose lo mantienen apagado.

Comprobado que el guardarraíl muerde: quitando el flag de `_DEV_ONLY_FLAGS` fallan
4 casos, entre ellos el del `config.yaml` en producción.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_dev_role_promotion_gate.py -q
# → 14 passed
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 503 passed
python scripts/validate_specs.py   # → [OK]
```

### Definition of Done (AC4)

- [x] **AC4** — con `DEBUG=false` el valor efectivo es `False` aunque lo active un
  `config.yaml`, y `dev/promote-reviewer` responde `403`.
- [x] Tests que cubren el cambio, en verde (14 nuevos; 503 en la suite).
- [x] Docs: **AC4 marcado en SPEC-015**; el porqué vive en el comentario de
  `_DEV_ONLY_FLAGS`.
- [x] Sin secretos en el diff.
- [x] Rama con prefijo `sec/` hacia `develop`.

### Cierre de la épica E1

Con T1.5, **E1 (Identidad y sesión) queda completa**: registro seguro y RBAC
(T1.1), rate limiting y lockout (T1.2), revocación de token y refresh (T1.3),
ticket efímero para SSE (T1.4), gate del atajo de promoción (T1.5) y seeds de
credenciales tras flag (T1.6). Los seis criterios de SPEC-015 están marcados.
