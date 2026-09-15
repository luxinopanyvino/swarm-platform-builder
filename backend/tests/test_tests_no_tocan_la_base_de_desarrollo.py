"""La suite nunca corre contra la base de desarrollo (ver `conftest.py`).

Un subconjunto de tests cuyo primer fichero no fijaba `DATABASE_URL` dejó que
`config.yaml` decidiera la base, y un fixture con `drop_all` vació
`backend/data/dev.db`.
"""
import os
import subprocess
import sys
from pathlib import Path

from conftest import DIRECTORIO_DE_DESARROLLO, ROOT_DIR, motivo_para_rechazar_url


def test_la_base_efectiva_de_la_sesion_no_es_la_de_desarrollo():
    from app.core.config import settings

    assert motivo_para_rechazar_url(settings.DATABASE_URL, Path.cwd()) is None, settings.DATABASE_URL


def test_rechaza_la_base_de_desarrollo_relativa_y_absoluta():
    assert motivo_para_rechazar_url("sqlite+aiosqlite:///./data/dev.db", ROOT_DIR)
    assert motivo_para_rechazar_url("sqlite+aiosqlite:///./backend/data/dev.db", ROOT_DIR.parent)
    absoluta = (DIRECTORIO_DE_DESARROLLO / "dev.db").as_posix()
    assert motivo_para_rechazar_url(f"sqlite+aiosqlite:///{absoluta}", Path("/"))


def test_rechaza_lo_que_no_es_sqlite():
    assert motivo_para_rechazar_url("postgresql+asyncpg://u:p@localhost/alejandria", ROOT_DIR)


def test_acepta_ficheros_temporales_y_memoria(tmp_path):
    assert motivo_para_rechazar_url(f"sqlite+aiosqlite:///{(tmp_path / 't.db').as_posix()}", ROOT_DIR) is None
    assert motivo_para_rechazar_url("sqlite+aiosqlite:///./test_egress.db", ROOT_DIR) is None
    assert motivo_para_rechazar_url("sqlite+aiosqlite:///:memory:", ROOT_DIR) is None


def test_la_sesion_se_aborta_si_el_entorno_apunta_a_la_base_de_desarrollo():
    """La guarda de verdad: con el entorno apuntando a `data/`, pytest sale sin ejecutar.

    Se lanza un test inofensivo de este mismo fichero. La sonda es un fichero que
    no existe dentro de `data/`: la guarda rechaza todo ese directorio, y así ni un
    fallo de la guarda podría tocar la `dev.db` de quien corre la suite.
    """
    sonda = DIRECTORIO_DE_DESARROLLO / "sonda-guarda-tests.db"
    entorno = {
        **os.environ,
        "DATABASE_URL": f"sqlite+aiosqlite:///{sonda.as_posix()}",
        "DEBUG": "true",
        "SECRET_KEY": "ci-secret-not-for-prod",
    }
    nodo = f"{Path(__file__).name}::test_rechaza_lo_que_no_es_sqlite"
    resultado = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"tests/{nodo}"],
        cwd=ROOT_DIR, env=entorno, capture_output=True, text=True, timeout=120,
    )
    salida = resultado.stdout + resultado.stderr
    assert resultado.returncode == 2, salida
    assert "base de desarrollo" in salida, salida
    assert "passed" not in salida, salida
    assert not sonda.exists()
