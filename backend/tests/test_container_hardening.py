"""Contenedores sin root e imagen final sin toolchain (SPEC-017 / T3.3 / AC3).

AC3: los contenedores corren con `USER` no root y la imagen final del backend no
incluye `build-essential` ni toolchain de compilación.

Sin Docker no se puede construir la imagen aquí, así que estos tests leen los
Dockerfiles y el compose. No sustituyen a un `docker build` —eso se dice en la PR—
pero sí fijan las tres cosas que se rompen solas con el tiempo: que alguien quite el
`USER`, que reaparezca el compilador en la etapa final, y que la aplicación empiece
a escribir en una ruta que el usuario sin privilegios no puede tocar.
"""
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = ROOT_DIR.parent
sys.path.insert(0, str(ROOT_DIR))

BACKEND_DOCKERFILE = ROOT_DIR / "Dockerfile"
FRONTEND_DOCKERFILE = REPO_DIR / "frontend" / "Dockerfile"
NGINX_CONF = REPO_DIR / "frontend" / "nginx.conf"
COMPOSE = REPO_DIR / "docker-compose.yml"

TOOLCHAIN = ("build-essential", "gcc", "g++", "make", "cmake", "libc6-dev")


def _stages(dockerfile: Path) -> list[list[str]]:
    """Parte un Dockerfile en etapas por cada `FROM`, sin comentarios ni vacíos."""
    stages: list[list[str]] = []
    for raw in dockerfile.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.upper().startswith("FROM "):
            stages.append([])
        if stages:
            stages[-1].append(line)
    return stages


def _final_stage(dockerfile: Path) -> list[str]:
    return _stages(dockerfile)[-1]


def _compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# AC3 — el backend no corre como root
# --------------------------------------------------------------------------- #

def test_the_backend_image_is_multi_stage():
    assert len(_stages(BACKEND_DOCKERFILE)) >= 2, "sigue siendo de una sola etapa"


def test_the_backend_final_stage_drops_to_a_non_root_user():
    usuarios = [l.split(None, 1)[1].strip() for l in _final_stage(BACKEND_DOCKERFILE)
                if l.upper().startswith("USER ")]
    assert usuarios, "la etapa final no baja de privilegios: falta USER"
    assert usuarios[-1] not in ("root", "0"), f"corre como {usuarios[-1]}"


def test_the_backend_user_is_created_before_it_is_used():
    """Un `USER app` sin `useradd` arranca con un UID numérico sin nombre ni home."""
    final = "\n".join(_final_stage(BACKEND_DOCKERFILE))
    assert "useradd" in final or "adduser" in final


def test_the_user_switch_is_the_last_privileged_step():
    """Si después del USER hay un RUN que necesita root, la imagen no construye."""
    final = _final_stage(BACKEND_DOCKERFILE)
    indice_user = max(i for i, l in enumerate(final) if l.upper().startswith("USER "))
    posteriores = [l.split()[0].upper() for l in final[indice_user + 1:]]
    assert not ({"RUN", "COPY", "ADD"} & set(posteriores)), (
        f"pasos privilegiados después del USER: {posteriores}"
    )


# --------------------------------------------------------------------------- #
# AC3 — y no lleva compilador
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("herramienta", TOOLCHAIN)
def test_the_toolchain_never_reaches_the_final_image(herramienta):
    final = "\n".join(_final_stage(BACKEND_DOCKERFILE))
    assert herramienta not in final, f"{herramienta} sigue en la imagen final"


def test_the_toolchain_does_live_in_the_builder():
    """Comprobación de que el test anterior mide algo: el compilador existe, pero antes."""
    builder = "\n".join(_stages(BACKEND_DOCKERFILE)[0])
    assert "build-essential" in builder


def test_the_final_stage_reuses_the_builder_output():
    final = "\n".join(_final_stage(BACKEND_DOCKERFILE))
    assert "--from=builder" in final, "la etapa final reinstala en vez de copiar"


def test_dependencies_are_still_installed_with_hash_checking():
    """El multi-stage no puede haberse llevado por delante la verificación de T6.3."""
    completo = BACKEND_DOCKERFILE.read_text(encoding="utf-8")
    assert "--require-hashes" in completo


def test_the_final_image_still_has_python_for_the_healthcheck():
    """La sonda de T3.5 es `python healthcheck.py`: si desaparece Python, deja de proteger."""
    assert _final_stage(BACKEND_DOCKERFILE)[0].lower().startswith("from python:")


# --------------------------------------------------------------------------- #
# AC3 — el frontend tampoco
# --------------------------------------------------------------------------- #

def test_the_frontend_runs_unprivileged():
    final = "\n".join(_final_stage(FRONTEND_DOCKERFILE))
    sin_privilegios = "nginx-unprivileged" in final
    usuarios = [l.split(None, 1)[1].strip() for l in _final_stage(FRONTEND_DOCKERFILE)
                if l.upper().startswith("USER ")]
    baja_usuario = bool(usuarios) and usuarios[-1] not in ("root", "0")
    assert sin_privilegios or baja_usuario, "el frontend sigue corriendo como root"


def test_nginx_listens_above_the_privileged_range():
    """Por debajo de 1024 hace falta un privilegio que este contenedor ya no tiene."""
    puertos = [int(m) for m in re.findall(r"listen\s+(\d+)", NGINX_CONF.read_text(encoding="utf-8"))]
    assert puertos, "nginx.conf no declara ningún listen"
    assert all(p >= 1024 for p in puertos), f"puertos privilegiados: {puertos}"


def test_the_spa_fallback_survived_the_rewrite():
    """React Router deja de funcionar en silencio si se pierde el try_files."""
    assert "try_files" in NGINX_CONF.read_text(encoding="utf-8")


def test_the_compose_publishes_the_port_nginx_actually_listens_on():
    puerto_nginx = int(re.search(r"listen\s+(\d+)", NGINX_CONF.read_text(encoding="utf-8")).group(1))
    mapeos = _compose()["services"]["frontend"]["ports"]
    destinos = {int(str(m).split(":")[-1]) for m in mapeos}
    assert puerto_nginx in destinos, f"nginx escucha en {puerto_nginx} y el compose publica {mapeos}"


def test_the_frontend_healthcheck_targets_that_same_port():
    """Apuntar al 80 aquí dejaría el contenedor marcado insano para siempre."""
    puerto_nginx = re.search(r"listen\s+(\d+)", NGINX_CONF.read_text(encoding="utf-8")).group(1)
    healthcheck = " ".join(_compose()["services"]["frontend"]["healthcheck"]["test"])
    assert f":{puerto_nginx}" in healthcheck


def test_the_published_host_port_did_not_change():
    """ALLOWED_ORIGINS y VITE_API_URL apuntan al 8080 del host: no puede moverse."""
    mapeos = _compose()["services"]["frontend"]["ports"]
    assert any(str(m).startswith("8080:") for m in mapeos)


# --------------------------------------------------------------------------- #
# AC3 — lo que de verdad rompe: rutas escribibles
# --------------------------------------------------------------------------- #

def _runtime_write_paths() -> dict[str, str]:
    """Rutas que la aplicación escribe, leídas del código y no de una lista a mano."""
    from app.modules.agents.application.use_cases import _LOGS_DIR

    return {
        "logs": f"/app/{_LOGS_DIR}",
        "rag_local": "/app/app/.rag_local",
        "assets": "/app/app/.assets",
    }


@pytest.mark.parametrize("nombre", sorted(_runtime_write_paths()))
def test_every_writable_path_is_backed_by_a_named_volume(nombre):
    """El fallo real de correr sin root: escribir donde no se puede.

    Un volumen nombrado hereda el propietario del directorio de la imagen —creado
    con dueño `app`—, mientras que el bind mount trae los permisos del host.
    """
    ruta = _runtime_write_paths()[nombre]
    montajes = _compose()["services"]["backend"]["volumes"]
    destinos = {str(m).split(":")[1] for m in montajes if ":" in str(m)}
    assert ruta in destinos, f"{ruta} no tiene volumen; el proceso no root no podrá escribir"


@pytest.mark.parametrize("nombre", sorted(_runtime_write_paths()))
def test_the_image_creates_those_paths_owned_by_the_app_user(nombre):
    """Si no existen con dueño `app`, Docker crea el volumen como root."""
    ruta = _runtime_write_paths()[nombre]
    final = "\n".join(_final_stage(BACKEND_DOCKERFILE))
    assert ruta in final, f"{ruta} no se crea en la imagen"
    assert "chown" in final


def test_runtime_data_is_kept_out_of_the_image():
    ignorados = (ROOT_DIR / ".dockerignore").read_text(encoding="utf-8")
    for ruta in ("logs/", "app/.assets/", "app/.rag_local/"):
        assert ruta in ignorados, f"{ruta} se hornearía dentro de la imagen"
