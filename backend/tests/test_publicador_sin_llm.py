"""SPEC-032 AC9 / T20.12 — el Publicador no usa LLM, tampoco en la traza (PR-REG-11)."""
import ast
from pathlib import Path

import pytest

from app.modules.agents.adapters import publicador
from app.modules.agents.domain import alejandria
from app.platform.engine.agents import uses_llm


@pytest.fixture(autouse=True)
def _registro():
    alejandria.register()


def test_el_modulo_del_publicador_no_importa_ni_invoca_el_llm():
    arbol = ast.parse(Path(publicador.__file__).read_text(encoding="utf-8"))
    nombres = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom):
            nombres |= {a.name for a in nodo.names}
            assert "llm" not in (nodo.module or "").split(".")[-1:]
        elif isinstance(nodo, ast.Import):
            nombres |= {a.name.split(".")[-1] for a in nodo.names}
        elif isinstance(nodo, ast.Name):
            nombres.add(nodo.id)
    assert not {"call_llm", "call_llm_stream", "resolve_agent_model"} & nombres


def test_el_publicador_no_declara_capacidades_de_llm():
    assert uses_llm("publicador") is False


@pytest.mark.parametrize("agente", ["investigador", "redactor", "revisor", "formateador"])
def test_los_agentes_con_llm_lo_declaran(agente):
    assert uses_llm(agente) is True


def test_un_agente_desconocido_se_considera_con_llm():
    assert uses_llm("agente-dinamico-de-un-agent-md") is True


def test_la_traza_del_paso_condiciona_el_modelo_a_uses_llm():
    from app.modules.agents.application import use_cases

    fuente = Path(use_cases.__file__).read_text(encoding="utf-8")
    assert "if uses_llm(agent_name) else None" in fuente
