"""SPEC-032 AC15 / T20.7 — el Revisor no aprueba por defecto (PR-REG-04)."""
import asyncio

import pytest

import app.modules.agents.adapters.revisor as revisor
from app.platform.explainability import decision_of
from app.platform.publication_gate.review import judgment_blockers, review_approves


def _run(respuesta=None, error=None, **extra):
    async def llm(*a, **k):
        if error:
            raise error
        return respuesta

    original = revisor.call_llm
    revisor.call_llm = llm
    try:
        state = {"draft_text": "Un borrador.", "loop_count": 0, "agent_settings": {}, **extra}
        return asyncio.run(revisor.run_revisor(state))
    finally:
        revisor.call_llm = original


@pytest.mark.parametrize(
    "respuesta",
    [
        "no es json",
        "{ esto tampoco }",
        '{"coherent": true, "feedback": []}',        # sin approval_score
        '{"approval_score": "alto", "feedback": []}',
        '{"approval_score": 250, "feedback": []}',   # fuera de rango
        '{"approval_score": true, "feedback": []}',
        "",
    ],
)
def test_respuesta_no_interpretable_es_not_verified(respuesta):
    out = _run(respuesta)
    assert out["review_status"] == "not_verified"
    assert out["coherent"] is False
    assert out["feedback"] == []          # no se inventan comentarios
    assert out["approval_score"] == 0     # ni 85 ni 75 ni 90
    assert judgment_blockers(out) == ["review_not_verified"]


def test_fallo_del_llm_no_inventa_una_revision():
    out = _run(error=RuntimeError("timeout"))
    assert out["review_status"] == "not_verified"
    assert out["feedback"] == []
    assert out["approval_score"] == 0


def test_no_verificada_no_pregunta_a_la_persona():
    llamadas = []

    async def pedir(_):
        llamadas.append(1)
        return "continue"

    out = _run("basura", _request_decision=pedir)
    assert llamadas == [] and out["user_decision"] is None


def test_respuesta_valida_sigue_funcionando():
    out = _run('{"approval_score": 91, "coherent": true, "feedback": ["bien"]}')
    assert out["review_status"] == "ok"
    assert out["approval_score"] == 91 and out["coherent"] is True
    assert out["feedback"] == ["bien"]
    assert review_approves(out)
    assert out["loop_count"] == 0


def test_respuesta_valida_que_rechaza_cuenta_la_vuelta():
    out = _run('{"approval_score": 60, "coherent": false, "feedback": ["flojo"]}')
    assert out["review_status"] == "ok" and out["loop_count"] == 1
    assert judgment_blockers(out) == ["score_below_threshold", "not_coherent"]


def test_un_80_con_incoherencia_no_aprueba():
    r = {"approval_score": 80, "coherent": False, "review_status": "ok"}
    assert not review_approves(r)
    assert review_approves({"approval_score": 80, "coherent": True, "review_status": "ok"})


def test_la_traza_no_registra_puntuacion_en_una_revision_no_verificada():
    d = decision_of(_run("basura"))
    assert d["score"] is None and d["review_status"] == "not_verified"
    d = decision_of(_run('{"approval_score": 90, "coherent": true, "feedback": []}'))
    assert d["score"] == 90 and d["review_status"] == "ok"
