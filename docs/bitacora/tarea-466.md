# Tarea #466 — Apuntar el repositorio y la CI a onpremialabs

## 2026-10-22 — Éxito ✅

- **Rama:** `chore/repo-onpremialabs`
- **PR:** la de esta rama → `develop` (`Closes #466`)
- **Origen:** el repositorio vive en `onpremialabs/swarm-platform-builder`; la cuenta `luxinopanyvino` ya no existe ni debe volver a usarse. El
  remoto local aún apuntaba al nombre antiguo y, al redirigir, las ramas empujadas no llegaban a la PR a tiempo (la CI de #465 no arrancó
  con el commit nuevo).

### Qué se hizo y dónde

- **Remoto local:** `origin` → `https://github.com/onpremialabs/swarm-platform-builder.git` (configuración de cada clon, no se versiona).
- **Agentes y comandos de desarrollo** (`.claude/agents/sdd-sync.md`, `task-runner.md`, `.claude/commands/resolve-task.md`): el `--repo` de los
  `gh` pasa a `onpremialabs/swarm-platform-builder`.
- **`.github/CODEOWNERS`** y **`claude-daily-digest.yml`** (`DIGEST_RECIPIENT`): propietario `@onpremialabs`.
- **Scripts** (`build_onboarding.py`, `seed_github_project.py`, `delete_github_project.py`), **README**, la página de onboarding generada y tres
  bitácoras antiguas: enlaces a issues y proyectos con el propietario nuevo.
- Sustitución literal `luxinopanyvino` → `onpremialabs`; `grep` posterior sin coincidencias fuera de `node_modules` y `storage/`.

### Definition of Done

- [x] Ninguna referencia a `luxinopanyvino` en el árbol versionado.
- [ ] La CI de esta PR corre contra `onpremialabs/swarm-platform-builder`.

### Fuera de alcance / notas

- Los números de proyecto (7 y 8) se conservan: se asume que el tablero se movió con el mismo número. Si no, hay que corregirlos.
- El HTML de onboarding está generado; la próxima ejecución de `build_onboarding.py` lo regenera con el propietario nuevo.
