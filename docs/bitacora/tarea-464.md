# Tarea #464 — Actualizar dependencias con vulnerabilidades (pip-audit en rojo)

## 2026-10-21 — Éxito ✅

- **Rama:** `sec/actualizar-dependencias-audit`
- **PR:** la de esta rama → `develop` (`Closes #464`)
- **Origen:** el job `Cadena de suministro · pip-audit + npm audit` estaba rojo en cada PR (también en las de E20) y enmascaraba cualquier fallo nuevo.

### Dónde estaba el problema

`pip-audit` sobre `backend/requirements.txt` daba **18 vulnerabilidades conocidas**:

| Paquete | Versión | Avisos | Corregido en |
|---|---|---|---|
| `certifi` | 2026.7.22 | 1 | 2026.10.19 |
| `urllib3` | 2.7.0 | 3 | 2.8.0 |
| `pypdf` | 6.16.2 | 8 | 6.19.0 (la más alta exigida) |
| `python-jose` | 3.5.0 | 1 (`PYSEC-2026-4298`) | **no hay versión con arreglo** |

### Qué se hizo y por qué

- **Lock** (`backend/requirements.txt`): suben `certifi` → 2026.10.19, `urllib3` → 2.8.0 y `pypdf` → 6.21.2 (la última; cubre todo
  hasta 6.19.0). Se recompiló con `pip-compile` bajo Python 3.12 (`uv run --python 3.12 --with pip-tools …`) y **solo se
  traspasaron al lock original los bloques de esos tres paquetes**: compilar en Windows quita `uvloop` por su marcador
  `sys_platform != "win32"` y el lock debe seguir siendo el de Linux. El diff es de 9 líneas (3 versiones y 6 hashes); los tres
  paquetes son Python puro, así que sus hashes no dependen de la plataforma.
- **`python-jose` — excepción documentada, no arreglo.** `PYSEC-2026-4298` (algoritmo confundido por una clave pública en DER) afecta a
  quien llama a `jwt.decode` sin restringir `algorithms` y con claves asimétricas. Aquí `app/core/security.py` firma y verifica con
  **HS256 y una clave simétrica** (`SECRET_KEY`), y el único `jwt.decode` pasa `algorithms=[settings.ALGORITHM]`. Se añade
  `--ignore-vuln PYSEC-2026-4298` en `ci.yml` con ese razonamiento, junto a la de `PYSEC-2026-1325` que ya existía por el mismo motivo.
- **Frontend (`npm audit`, 1 alto):** el job también falló por `follow-redirects` 1.16.0 (dos avisos, `GHSA-q3jh-wrc6-jgq8` y
  `GHSA-8r9p-f939-6h3c`), dependencia transitiva con arreglo sin cambio de versión mayor. `npm audit fix` la sube a **1.16.1**; el diff
  de `frontend/package-lock.json` es de 3 líneas. Los dos avisos **moderados** de `react-router` siguen: solo se arreglan con un salto
  de versión mayor (`--force`), que `ci.yml` ya documenta como tarea aparte, y el job solo bloquea en `high`.
- **Test que sostiene las dos excepciones** (`backend/tests/test_jwt_algorithm_pinned.py`, 4 casos): falla si el algoritmo deja de ser
  HMAC, si algún `jwt.decode` no restringe `algorithms`, si aparece otro uso de `jose` o si la CI pierde las excepciones. Así dejan
  de ser una tolerancia silenciosa.

### Definition of Done

- [x] `npm audit --omit=dev --audit-level=high` → sale con 0; `npm run build` y `npm run build:public` pasan.
- [x] `pip-audit --require-hashes -r requirements.txt --ignore-vuln PYSEC-2026-1325 --ignore-vuln PYSEC-2026-4298` → «No known
  vulnerabilities found».
- [x] El lock se instala con `--require-hashes` en un Python 3.12 limpio y la suite pasa con las versiones nuevas: **1392 pasados, 4
  fallos que ya tenía `develop`** (`test_frontend_layers` ×2 por rutas con `\` de Windows —arreglados en #463—,
  `test_no_tracked_databases` por un bloqueo de archivo de Windows y `test_la_spec_de_finetune_sigue_en_draft` de SPEC-031).
- [ ] La CI de esta PR es la comprobación en Linux.

### Verificación

`pip-audit` 2.10.1 en local contra el lock nuevo, e instalación con hashes + suite completa en un entorno 3.12 limpio.

### Fuera de alcance / notas

- **`python-jose` sigue instalado y sin arreglo.** La salida real es migrar a otra librería (p. ej. PyJWT) o quitar la excepción cuando
  haya versión corregida; no se hizo aquí porque cambia el código de autenticación y merece su propia tarea y pruebas.
- Quedan avisos de `npm audit` de severidad moderada (`follow-redirects`, `react-router`); el job solo bloquea en `high`/`critical` y
  los lista como informativos. No se tocan aquí.
- Las dependencias seguirán envejeciendo: Dependabot ya está activo, pero el lock con hashes se recompila a mano.
