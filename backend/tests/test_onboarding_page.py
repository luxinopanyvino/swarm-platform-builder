"""La guía para colaboradores se genera desde las specs y no se queda atrás.

`docs/public/onboarding/alejandria-por-dentro.html` sale de `scripts/build_onboarding.py`,
que lee tareas, dependencias y criterios de las specs, y lo editorial de
`docs/onboarding/*.yaml`. Estos tests fallan si el contenido editorial apunta a tareas
o componentes que ya no existen, o si el lector de specs deja de entender su formato.
Se ejecutan sin red: el estado de los issues sale de la copia `issues.json`.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_onboarding.py"


def _modulo():
    spec = importlib.util.spec_from_file_location("build_onboarding", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_la_guia_se_genera_sin_red_y_sin_incoherencias(tmp_path):
    salida = tmp_path / "guia.html"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--sin-github", "--estricto", "--salida", str(salida)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    assert r.returncode == 0, r.stdout + r.stderr
    html = salida.read_text(encoding="utf-8")
    assert "const DATA" in html
    assert "/resolve-task" in html, "la guía debe explicar cómo ejecutar una tarea"
    assert "build_onboarding.py" in html, "la guía debe explicar cómo regenerarse"


def test_el_lector_de_criterios_une_las_lineas_de_continuacion():
    mod = _modulo()
    texto = (
        "## 3. Criterios de aceptación\n\n"
        "- [ ] **AC1** — *Given* algo, *When* pasa,\n"
        "  *Then* `ocurre` otra cosa.\n"
        "- [x] **AC2** — Segundo criterio.\n\n"
        "## 4. Diseño\n"
    )
    acs = mod.criterios(texto)
    assert acs == {"AC1": "*Given* algo, *When* pasa, *Then* `ocurre` otra cosa.", "AC2": "Segundo criterio."}
    assert mod.md_a_html(acs["AC1"]) == "<em>Given</em> algo, <em>When</em> pasa, <em>Then</em> <code>ocurre</code> otra cosa."


def test_el_lector_de_criterios_no_confunde_la_seccion_3_0_con_la_3():
    """SPEC-031 tiene «## 3.0 Preguntas abiertas» antes de «## 3. Criterios»."""
    mod = _modulo()
    texto = (
        "## 3.0 Preguntas abiertas\n\n1. ¿Algo?\n\n"
        "## 2. Objetivos\n\nNada.\n\n"
        "## 3. Criterios de aceptación (Given/When/Then)\n\n"
        "- [ ] **AC1** — Primero.\n"
        "- [ ] **AC4** — Último, al final del fichero."
    )
    assert mod.criterios(texto) == {"AC1": "Primero.", "AC4": "Último, al final del fichero."}


def test_una_tarea_de_una_spec_ready_aparece_aunque_no_tenga_issue_ni_ficha():
    mod = _modulo()
    specs = [dict(
        id="SPEC-999", archivo="SPEC-999-x.md", estado="ready",
        epica={"id": "E99", "title": "Épica de prueba", "area": "area/qa"},
        tareas=[{"id": "T99.1", "title": "Primera", "sev": "high", "depends_on": [], "acceptance": ["AC1"]},
                {"id": "T99.2", "title": "Segunda", "sev": "low", "depends_on": ["T99.1"], "acceptance": []}],
        acs={"AC1": "*Given* x, *Then* y."},
    )]
    avisos = []
    modelo = mod.construir(specs, {}, {}, {"componentes": []}, avisos)
    por_id = {t["id"]: t for t in modelo["tareas"]}
    assert set(por_id) == {"T99.1", "T99.2"}
    assert por_id["T99.1"]["estado"] == "sin-issue"
    assert por_id["T99.2"]["ola"] == 1, "una dependencia abierta empuja a la ola siguiente"
    assert por_id["T99.1"]["unlocks"] == ["T99.2"]
    assert any("sin ficha" in a for a in avisos)


def test_una_dependencia_cerrada_no_bloquea():
    mod = _modulo()
    specs = [dict(
        id="SPEC-999", archivo="SPEC-999-x.md", estado="ready",
        epica={"id": "E99", "title": "Épica", "area": "area/qa"},
        tareas=[{"id": "T99.1", "title": "Hecha", "sev": "low", "depends_on": [], "acceptance": []},
                {"id": "T99.2", "title": "Siguiente", "sev": "low", "depends_on": ["T99.1"], "acceptance": []}],
        acs={},
    )]
    issues = {"T99.1": {"n": 1, "estado": "closed"}, "T99.2": {"n": 2, "estado": "open"}}
    modelo = mod.construir(specs, issues, {}, {"componentes": []}, [])
    [t] = modelo["tareas"]
    assert t["id"] == "T99.2" and t["estado"] == "lista" and t["ola"] == 0
    assert modelo["cerradas"] == {"T99.1": {"title": "Hecha", "n": 1}}
