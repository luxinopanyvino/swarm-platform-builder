"""Alta del área `area/qa` y coherencia del plan de QA/evaluación (SPEC-026, SPEC-027).

Dar de alta un área es tocar cuatro sitios —validador, seed del Project, gobernanza
y backlog— y hacerlo en tres deja el validador rechazando specs perfectamente
válidas, o el seed sin la etiqueta que los issues van a pedir. Ya se probó así para
`area/evaluation` en T9.6; esto es lo mismo para `area/qa`.

La coherencia de los bloques `sdd-sync` —épicas que no se pisan, dependencias con
destino, criterios de aceptación que alguna tarea reclama— vive en
`test_spec_plan_coherence.py`, donde se comprueba sobre **todas** las specs.
"""
import re
from collections import Counter
from pathlib import Path

import pytest
import yaml

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
VALIDADOR = REPO_DIR / "scripts" / "validate_specs.py"
SEED = REPO_DIR / "scripts" / "seed_github_project.py"
GOBERNANZA = REPO_DIR / "docs" / "governance" / "GOVERNANCE.md"
BACKLOG = REPO_DIR / "docs" / "backlog" / "security-hardening-backlog.md"
SPECS_DIR = REPO_DIR / "docs" / "specs"

AREA = "area/qa"


# ── El alta, en los cuatro sitios ────────────────────────────────────────────

@pytest.mark.parametrize("nombre,ruta", [
    ("validador", VALIDADOR),
    ("seed del Project", SEED),
    ("gobernanza", GOBERNANZA),
    ("backlog", BACKLOG),
])
def test_el_area_esta_dada_de_alta(nombre, ruta):
    assert AREA in ruta.read_text(encoding="utf-8"), f"{AREA} no aparece en el {nombre}"


def test_el_validador_acepta_specs_del_area():
    """No basta con que la cadena aparezca: tiene que estar en la lista que decide."""
    from importlib import util

    spec = util.spec_from_file_location("validate_specs_qa", VALIDADOR)
    modulo = util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    assert AREA in modulo.ALLOWED_AREAS


def test_el_seed_declara_la_etiqueta_con_color():
    """El seed crea las labels; una que falte deja los issues sin su área."""
    texto = SEED.read_text(encoding="utf-8")
    assert re.search(rf'\("{re.escape(AREA)}",\s*"[0-9a-f]{{6}}",', texto), (
        f"{AREA} no está en LABELS con color válido"
    )


# ── El ADR que sostiene SPEC-027 ─────────────────────────────────────────────
# La coherencia de los bloques `sdd-sync` (épicas, dependencias, cobertura de AC)
# se prueba en test_spec_plan_coherence.py, para todas las specs y no solo para
# estas dos. Duplicarla aquí sería tener dos sitios diciendo lo mismo.

def test_el_adr_de_deepeval_existe_y_lo_enlaza_su_spec():
    adr = REPO_DIR / "docs" / "adr" / "0010-adopt-deepeval-as-metrics-library.md"
    assert adr.is_file()
    spec = (SPECS_DIR / "SPEC-027-model-evaluation-deepeval.md").read_text(encoding="utf-8")
    assert "0010-adopt-deepeval-as-metrics-library" in spec
