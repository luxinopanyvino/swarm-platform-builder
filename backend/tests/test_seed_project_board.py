"""Siembra del tablero desde las specs (`scripts/seed_project_board.py`).

El script tiene dos mitades y solo una se puede probar aquí: la lectura de specs y
el cálculo del plan son puras, y el borde con `gh` habla con Projects v2, que solo
existe en GraphQL —bloqueado en las sesiones de Claude Code—. De ahí la forma del
script: toda la decisión vive en funciones sin red, y lo que toca GitHub es una
capa fina que no decide nada. Lo que estos casos defienden es justo eso.

El fallo que persiguen es el de su antecesor. `seed_github_project.py` lleva las
épicas escritas a mano (E1–E6, 28 tareas) y no lee ninguna spec, así que quedó
congelado en junio y hoy sembraría un backlog que ya no existe. Aquí la fuente es
la spec, y si alguien vuelve a fijar la lista en el código, `test_la_definicion_sale_de_las_specs_y_no_de_una_lista_fija` cae.
"""
import sys
from importlib import util
from pathlib import Path

import pytest

REPO_DIR = Path(__file__).resolve().parents[2]
SCRIPT = REPO_DIR / "scripts" / "seed_project_board.py"


@pytest.fixture(scope="module")
def board():
    spec = util.spec_from_file_location("seed_project_board", SCRIPT)
    modulo = util.module_from_spec(spec)
    sys.modules["seed_project_board"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def _spec(tmp_path, nombre, estado, epica, tareas):
    tareas_yaml = "\n".join(
        f'  - id: {t}\n    title: "tarea {t}"\n    sev: low\n    depends_on: []\n    acceptance: []'
        for t in tareas
    )
    (tmp_path / nombre).write_text(
        f"""# {nombre}

- **Estado:** {estado}

## 3. Criterios de aceptación

- [ ] **AC1** — algo

```yaml
# sdd-sync v1
epic:
  id: {epica}
  title: "épica {epica}"
  area: area/backend
tasks:
{tareas_yaml}
```
""",
        encoding="utf-8",
    )


# ── Lectura de las specs ─────────────────────────────────────────────────────

def test_una_spec_ready_aporta_su_epica_y_sus_tareas(board, tmp_path):
    _spec(tmp_path, "SPEC-100-x.md", "Ready", "E50", ["T50.1", "T50.2"])
    d = board.leer_definicion(tmp_path)
    assert set(d.marcadores) == {"epic:E50", "task:T50.1", "task:T50.2"}


@pytest.mark.parametrize("estado", ["Draft", "Superseded", "Rejected"])
def test_una_spec_que_no_sincroniza_no_aporta_nada(board, tmp_path, estado):
    """Misma regla que `validate_specs.py`: en `Draft` no hay issues que colocar.

    Es la salvaguarda de SPEC-031 (fine-tune): su bloque declara tareas y no debe
    llegar al tablero mientras la decisión no esté tomada.
    """
    _spec(tmp_path, "SPEC-101-x.md", estado, "E51", ["T51.1"])
    d = board.leer_definicion(tmp_path)
    assert d.marcadores == {}
    assert d.ignoradas == (("SPEC-101-x.md", estado),)


def test_una_epica_compartida_por_dos_specs_no_se_duplica(board, tmp_path):
    """Compartir épica es legítimo aquí: E2 la declaran SPEC-002, SPEC-016 y SPEC-024."""
    _spec(tmp_path, "SPEC-102-a.md", "Ready", "E52", ["T52.1"])
    _spec(tmp_path, "SPEC-103-b.md", "Done", "E52", ["T52.2"])
    d = board.leer_definicion(tmp_path)
    assert set(d.marcadores) == {"epic:E52", "task:T52.1", "task:T52.2"}


def test_la_definicion_sale_de_las_specs_y_no_de_una_lista_fija(board, tmp_path):
    """El pecado de `seed_github_project.py`, que se quedó congelado en E1–E6.

    Un directorio sin specs debe dar cero marcadores. Si alguien vuelve a incrustar
    la lista en el código, aquí aparecerían de la nada.
    """
    assert board.leer_definicion(tmp_path).marcadores == {}


# ── Marcadores ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("cuerpo,esperado", [
    ("<!-- sdd:epic:E14 -->\n**Spec:** …", "epic:E14"),
    ("<!-- sdd:task:T14.1 -->\ncosas", "task:T14.1"),
    ("<!--sdd:task:T9.1-->", "task:T9.1"),
    ("un issue normal sin marcador", None),
    (None, None),
    ("", None),
])
def test_extraccion_del_marcador(board, cuerpo, esperado):
    assert board.marcador_de(cuerpo) == esperado


def test_los_issues_sin_marcador_no_los_gestiona_el_sdd(board):
    indice = board.indexar_issues([
        {"number": 1, "body": "<!-- sdd:task:T1.1 -->", "html_url": "u1"},
        {"number": 2, "body": "issue a mano", "html_url": "u2"},
    ])
    assert set(indice) == {"task:T1.1"}


# ── El plan ──────────────────────────────────────────────────────────────────

def _definicion(board, marcas):
    return board.Definicion(marcadores={m: "" for m in marcas})


def test_planifica_solo_lo_que_falta(board):
    d = _definicion(board, ["task:T1.1", "task:T1.2"])
    indice = {
        "task:T1.1": {"number": 10, "html_url": "u10"},
        "task:T1.2": {"number": 11, "html_url": "u11"},
    }
    plan = board.planificar(d, indice, ["u10"])
    assert plan.anadir == [("task:T1.2", 11, "u11")]
    assert plan.presentes == ["task:T1.1"]


def test_es_idempotente(board):
    """Segunda pasada sobre un tablero ya sembrado: nada que hacer."""
    d = _definicion(board, ["task:T1.1"])
    indice = {"task:T1.1": {"number": 10, "html_url": "u10"}}
    plan = board.planificar(d, indice, ["u10"])
    assert not plan.hay_trabajo and plan.anadir == []


def test_un_marcador_sin_issue_se_reporta_y_no_rompe(board):
    """La frontera con `/sdd-sync`: este script coloca, no crea.

    Si la spec declara una tarea que nadie ha sembrado, decirlo es la respuesta
    útil; crearla aquí sería duplicar la competencia del agente y acabar con dos
    sitios creando issues.
    """
    d = _definicion(board, ["task:T1.1", "task:T9.9"])
    indice = {"task:T1.1": {"number": 10, "html_url": "u10"}}
    plan = board.planificar(d, indice, [])
    assert plan.sin_issue == ["task:T9.9"]
    assert plan.anadir == [("task:T1.1", 10, "u10")]


def test_no_propone_quitar_nada_del_tablero(board):
    """Un item ajeno al SDD es legítimo; este script no es quién para juzgarlo."""
    d = _definicion(board, ["task:T1.1"])
    indice = {"task:T1.1": {"number": 10, "html_url": "u10"}}
    plan = board.planificar(d, indice, ["u10", "url-de-algo-ajeno"])
    assert not hasattr(plan, "quitar")
    assert plan.presentes == ["task:T1.1"]


# ── Informe ──────────────────────────────────────────────────────────────────

def test_el_dry_run_dice_que_es_un_plan(board):
    d = _definicion(board, ["task:T1.1"])
    plan = board.planificar(d, {"task:T1.1": {"number": 10, "html_url": "u10"}}, [])
    texto = board.render(plan, d, "Tablero", aplicar=False)
    assert "--apply" in texto


def test_al_aplicar_no_se_ofrece_el_dry_run(board):
    d = _definicion(board, ["task:T1.1"])
    plan = board.planificar(d, {"task:T1.1": {"number": 10, "html_url": "u10"}}, [])
    assert "--apply" not in board.render(plan, d, "Tablero", aplicar=True)


def test_el_informe_manda_a_sdd_sync_cuando_falta_un_issue(board):
    d = _definicion(board, ["task:T9.9"])
    plan = board.planificar(d, {}, [])
    assert "sdd-sync" in board.render(plan, d, "Tablero", aplicar=False)


# ── El borde con gh ──────────────────────────────────────────────────────────

def test_sin_gh_el_error_explica_por_que(board, monkeypatch):
    """Es el caso de esta misma sesión: sin `gh`, el script debe decir qué falta."""
    def no_hay(*a, **k):
        raise FileNotFoundError

    monkeypatch.setattr(board.subprocess, "run", no_hay)
    with pytest.raises(board.GhNoDisponible) as error:
        board.gh("project", "list")
    assert "gh auth refresh -s project" in str(error.value)


#: Subcomandos de `gh issue` que este script no debe usar jamás. Colocar en el
#: tablero y gestionar issues son competencias distintas: si este script creara lo
#: que falta, habría dos sitios creando issues, que es el problema que `/sdd-sync`
#: existe para no tener.
VERBOS_PROHIBIDOS = {"create", "close", "edit", "delete", "reopen", "transfer"}


def _llamadas_a_gh(fuente: str):
    """`gh("issue", "create", …)` → ("issue", "create"). Sobre el AST, no por texto.

    La primera versión de este test buscaba la cadena `"issue create"` en el
    fichero. Nunca habría saltado: `gh()` recibe varargs, así que en el código real
    esos dos tokens van en literales separados. Lo descubrió una mutación que
    sustituyó el `item-add` por un `gh("issue", "create", …)` y **pasó en verde**.
    Un guardia que comprueba una forma que el código no puede tener no comprueba
    nada.
    """
    import ast

    for nodo in ast.walk(ast.parse(fuente)):
        if not isinstance(nodo, ast.Call):
            continue
        nombre = getattr(nodo.func, "id", None) or getattr(nodo.func, "attr", None)
        if nombre not in ("gh", "gh_json"):
            continue
        literales = [a.value for a in nodo.args
                     if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        if len(literales) >= 2:
            yield literales[0], literales[1]


def test_el_script_no_crea_ni_cierra_issues(board):
    culpables = [
        f"gh {sub} {verbo}"
        for sub, verbo in _llamadas_a_gh(SCRIPT.read_text(encoding="utf-8"))
        if sub == "issue" and verbo in VERBOS_PROHIBIDOS
    ]
    assert not culpables, f"el script gestiona issues en vez de solo colocarlos: {culpables}"


def test_el_guardia_de_alcance_reconoce_la_forma_real_de_la_llamada(board):
    """Que el propio guardia no vuelva a ser vacío.

    Si `_llamadas_a_gh` dejara de encontrar los dos primeros literales de una
    llamada, el test de arriba pasaría siempre y nadie se enteraría.
    """
    muestra = 'gh("issue", "create", "--title", x)\ngh("project", "item-add", "1")\n'
    assert set(_llamadas_a_gh(muestra)) == {("issue", "create"), ("project", "item-add")}
