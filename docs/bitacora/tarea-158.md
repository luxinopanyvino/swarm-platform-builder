# Tarea #158 — T1.6 Relegar seeds de credenciales débiles a flag de dev

## 2026-08-30 13:30 — Completada ✅

- **Rama:** `sec/158-dev-credential-seeds`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #158`)
- **Spec/ADR:** SPEC-015, Épica E1. Criterio vinculante: **AC5**.
- **Dependencias:** ninguna.

### El agujero

`ensure_local_admin_user` estaba condicionada a que **la base de datos fuese
SQLite**, un proxy de «esto es local» que no lo es: cualquier despliegue pequeño
sobre SQLite creaba `admin@admin` con contraseña conocida (`admin123`), sin
importar `DEBUG`. Lo mismo con los tres usuarios de prueba.

Y no solo los creaba. En cada arranque reimponía **contraseña, nombre, rol y estado
activo**:

```python
else:
    user.hashed_password = hash_password(admin_password)
    user.role = UserRole.ADMIN
    user.is_active = True
```

Es decir: cambiar la contraseña del admin o desactivar la cuenta se revertía solo
en el siguiente reinicio, en silencio. Sembrar una credencial conocida es una
comodidad de desarrollo; **reimponerla es quitarle al operador el control de su
propia cuenta**.

### Qué se hizo

**Flag explícito `ENABLE_DEV_SEED`**, apagado por defecto, y —lo importante— con
valor efectivo **`False` cuando `DEBUG=false`, venga de donde venga**: variable de
entorno o `config.yaml`. Eso convierte «acuérdate de apagarlo al desplegar» en algo
que no hace falta recordar. El mecanismo vive en `_disable_dev_only_flags`.

| `DEBUG` | `ENABLE_DEV_SEED` | Efectivo |
|---|---|---|
| true | true | **True** |
| true | false | False |
| false | **true** | **False** |
| false | false | False |

**La siembra crea, no reescribe.** Si la cuenta ya existe, no se toca: ni
contraseña, ni rol, ni estado.

**El contenido de demo también queda tras el flag** (artículos y flujos de
ejemplo), que es lo que pide AC5 al decir «el seed de demo». El **proyecto del
sistema y sus perfiles de agente siguen sembrándose siempre**: son configuración de
la plataforma, no demo, y sin ellos un despliegue limpio arranca inservible.

**El flujo local documentado sigue funcionando**: `dev-local.cmd` activa el flag, y
README, `docs/guide/auth.md` y `docs/guide/configuration.md` explican que esas
cuentas ahora requieren `DEBUG=true` **y** `ENABLE_DEV_SEED=true`.

### Decisiones documentadas

- **Se conserva `admin123` tras el flag.** El título de la tarea dice *relegar*, no
  eliminar, y AC5 solo prohíbe la siembra con `DEBUG=false`. Una contraseña
  aleatoria por log habría roto el flujo local documentado a cambio de poco: lo que
  hacía peligroso a `admin123` no era su fuerza, sino que apareciera sin querer.
- **El flag manda, no el motor de base de datos.** Un heurístico («es SQLite, luego
  es local») es justo lo que falló aquí.
- **`ENABLE_DEV_ROLE_PROMOTION` no se toca**, aunque el mecanismo nuevo le vendría
  como anillo al dedo (ver más abajo): es de otra tarea.

### Dos tests ajenos que había que arreglar

`test_seeded_public_user_login` y `test_admin_can_change_role` invocaban la siembra
y esperaban que sembrara. Ahora activan el flag, que es exactamente lo que hace un
entorno de desarrollo. No es un parche para que pasen: si un test necesita la cuenta
sembrada, tiene que optar por la siembra igual que optaría un desarrollador.

### Test nuevo

`backend/tests/test_dev_seed_flag.py` (20 casos), ejercitando **las funciones de
arranque de verdad**, no el flag por separado: lo que hay que garantizar es que
nadie siembre, no que la condición exista.

- **AC5**: por defecto no se crea ninguna cuenta; con `DEBUG=false` tampoco; la
  configuración fuerza el flag a `False` con `DEBUG=false`; las cuatro
  combinaciones de `DEBUG`×flag dan el valor efectivo esperado; y **SQLite ya no
  decide** — el fallo de origen, fijado como test.
- **La demo sigue viva bajo el flag**: se crean las cuatro cuentas, `admin123`
  funciona como promete el README, y `DEV_ADMIN_PASSWORD` la sustituye.
- **No se reescribe**: una contraseña ya cambiada sobrevive; una cuenta desactivada
  **no se reactiva** ni recupera su rol sembrado; sembrar dos veces no cambia nada.
- **Coherencia**: el valor por defecto es `False`, `dev-local.cmd` activa el flag
  —si no, el flujo local se rompería sin explicación—, el compose de producción
  nunca lo activa, y la documentación menciona el flag donde promete las cuentas.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_dev_seed_flag.py -q
# → 20 passed
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 489 passed
python scripts/validate_specs.py   # → [OK]
```

### Definition of Done (AC5)

- [x] **AC5** — con `DEBUG=false` no se siembran usuarios con credenciales débiles;
  el seed de demo solo corre bajo flag de dev explícito.
- [x] Tests que cubren el cambio, en verde (20 nuevos; 489 en la suite).
- [x] Docs: README, `docs/guide/auth.md`, `docs/guide/configuration.md`, los dos
  `config.yaml` y `dev-local.cmd`. **AC5 marcado en SPEC-015.**
- [x] Sin secretos nuevos en el diff.
- [x] Rama con prefijo `sec/` hacia `develop`.

### Seguimiento: **#157 (T1.5) sigue abierta y su AC no se cumple**

Al mirar la spec para esta tarea salió que **AC4 no está implementado**. Dice:

> *Given* `ENABLE_DEV_ROLE_PROMOTION` ausente **o un `config.yaml` que lo activa**,
> *When* `DEBUG=false`, *Then* el valor efectivo es `False`.

Hoy ese flag solo es fail-safe **cuando falta** (lo cubre
`test_secure_registration_rbac.py`); un `config.yaml` con `enable_dev_role_promotion:
true` y `DEBUG=false` **sí lo deja activo**. Tampoco hay bitácora de #157.

El arreglo es añadirlo a la tupla `_DEV_ONLY_FLAGS` que se crea aquí —una línea—,
pero es tarea suya y no la mezclo. Queda el mecanismo listo y anotado en el propio
código.
