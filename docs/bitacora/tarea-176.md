# Tarea #176 — T6.2 Escaneo de dependencias (pip-audit/npm audit) + Dependabot

## 2026-08-17 10:05 — Completada ✅

- **Rama:** `sec/176-177-supply-chain` (junto con #177)
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #176`)
- **Spec/ADR:** SPEC-020, ADR-0002/0004, Épica E6. Criterio vinculante: **AC2**.
- **Dependencias:** T6.1 (CI en PRs), ya implementada de facto.

### Por qué va en la misma rama que #177

T6.3 **depende de** T6.2 en el propio bloque `sdd-sync`, y ambas tocan
`.github/workflows/ci.yml`. Separarlas obligaría a apilar una PR cuyo único
contenido sería reeditar el mismo fichero, y el estado intermedio —el gate de
auditoría antes de que exista el lock que audita— no aporta nada. Cada tarea
conserva su bitácora.

### Qué se hizo

**`.github/dependabot.yml`**: tres ecosistemas —`pip` (`/backend`), `npm`
(`/frontend`) y **`github-actions`** (`/`)— semanales. Las Actions se incluyen
porque también son código de terceros que corre con acceso al repositorio, y son
las que más se olvidan. Minors y parches van agrupados para no inundar el
tablero; los avisos de seguridad llegan aparte y no se pierden dentro del grupo.

**Job `deps-audit` en CI**: `pip-audit` sobre el lock del backend y `npm audit`
sobre el frontend.

### La primera limpieza, que es lo que permite que el gate bloquee

La spec dice «no bloqueantes al inicio, bloqueantes tras la primera limpieza».
Hacer la limpieza ahora evita dejar un gate que avisa para siempre y que nadie
mira. Estado al empezar:

| | Antes | Después |
|---|---|---|
| Frontend (producción) | 5 (3 moderate, **2 high**) | **2 moderate** |
| Backend | 1 (ecdsa) | 1, ignorada con motivo |

Las dos `high` eran reales y en algo que sí usamos —subida de ficheros—:
**axios** (DoS por recursión en `formDataToJSON`) y **form-data** (inyección CRLF
en nombres de campo multipart). `npm audit fix` las resolvió sin tocar
`package.json`: solo se movió el lock, y ambos builds siguen pasando.

Cambios relevantes del lock: `axios 1.16.1 → 1.20.0`, `form-data 4.0.5 → 4.0.6`,
`@remix-run/router 1.23.2 → 1.23.4`, `react-router(-dom) 6.30.3 → 6.30.6`. Ningún
salto de major.

### Decisiones documentadas

- **El umbral del frontend es `high`, no `moderate`, y por un motivo concreto.**
  Las dos moderadas que quedan (open redirect en react-router) solo se arreglan
  subiendo a **react-router-dom 7.x**, un salto de major que exige probar el
  enrutado y merece su propia tarea. Bloquear en `moderate` dejaría la CI roja sin
  que nadie pueda arreglarla desde aquí. Se añade un paso **informativo** que
  imprime el inventario completo en cada ejecución para que las moderadas no se
  vuelvan deuda invisible.
- **`pip-audit` sí bloquea, con una excepción justificada en el sitio.**
  `PYSEC-2026-1325` afecta a `ecdsa`, que entra de forma transitiva por
  `python-jose` y **no tiene versión con arreglo**. El backend firma sus JWT con
  **HS256** (`ALGORITHM` en `app/core/config.py`), que es HMAC y no toca ECDSA. El
  motivo y la condición para retirarla —pasar a ES256— están escritos en el propio
  workflow, no en un fichero aparte que nadie abre.
- **Se audita el lock, no el entorno instalado**: es lo que se despliega de verdad.
- **`pip-audit` pineado** (`==2.10.1`): un escáner que cambia solo convierte la CI
  en algo no reproducible.

### Test nuevo

Compartido con #177: `backend/tests/test_supply_chain.py`. Para AC2 verifica que
existe el job `deps-audit`, que ejecuta **los dos** escáneres, que el de backend
**bloquea de verdad** (sin `|| true` ni `continue-on-error`), que toda
`--ignore-vuln` lleva explicación en el propio workflow, y que Dependabot cubre
los tres ecosistemas apuntando a directorios que existen, con periodicidad válida.

### Verificación

Códigos de salida comprobados a mano, que es lo único que demuestra que un gate
bloquea:

```
pip-audit --require-hashes -r requirements.txt                        -> exit 1
pip-audit --require-hashes -r requirements.txt --ignore-vuln PYSEC-…  -> exit 0
npm audit --omit=dev --audit-level=high                               -> exit 0
npm audit --omit=dev                                                  -> exit 1  (las 2 moderadas)
```

```
python -m pytest -q          # → 333 passed
npm run build && npm run build:public   # → ambos OK
```

### Definition of Done (AC2)

- [x] **AC2** — la CI incluye `pip-audit` + `npm audit` y Dependabot está
  configurado para backend, frontend y GitHub Actions.
- [x] Tests que cubren el cambio, en verde.
- [x] Docs: bloque de CI en `CLAUDE.md`.
- [x] Sin secretos en el diff.
- [x] Rama con prefijo `sec/` hacia `develop`.

### Seguimiento

**Subir a react-router-dom 7.x** para cerrar las dos moderadas de open redirect.
Es un major con migración de enrutado: tarea aparte, no un `audit fix --force`
metido de rondón en una PR de cadena de suministro.
