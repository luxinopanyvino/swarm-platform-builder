"""Tope de tokens de salida en el dispatcher LLM, y la síntesis del investigador.

Sin `num_predict`, Ollama no para nunca por su cuenta. Un modelo pequeño
(`nexus-science`, 1.5B) que entraba en bucle repitiendo frases dejaba la síntesis
del investigador generando hasta el timeout de 600 s — y el timeout es un error
transitorio, así que se reintentaba: hasta ~40 minutos con el log parado en
«Etapa 2/2 — Síntesis con LLM».
"""
import uuid

import pytest

import app.platform.llm as llm
from app.core import config
from app.modules.agents.adapters import investigador as adapter_investigador
from app.platform.capabilities import binding


@pytest.fixture(autouse=True)
def _sin_reintentos(monkeypatch):
    monkeypatch.setattr(llm, "_retry_params", lambda: (0, 0.0, 0.0))


# ── El dispatcher reenvía el tope a cada proveedor ───────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("proveedor, funcion", [
    ("ollama", "_call_ollama"),
    ("openai", "_call_openai"),
    ("anthropic", "_call_anthropic"),
])
async def test_call_llm_reenvia_max_tokens_al_proveedor(monkeypatch, proveedor, funcion):
    monkeypatch.setattr(config.settings, "LLM_PROVIDER", proveedor, raising=False)
    visto = {}

    async def falso(*args, **kwargs):
        visto.update(kwargs)
        return "ok"

    monkeypatch.setattr(llm, funcion, falso)
    await llm.call_llm("hola", model="m", max_tokens=321)
    assert visto.get("max_tokens") == 321


# ── Ollama: el tope viaja como `num_predict` ─────────────────────────────────

class _Respuesta:
    status_code = 200
    text = ""

    def json(self):
        return {"response": "texto", "prompt_eval_count": 1, "eval_count": 1}


def _cliente_que_captura(capturado):
    class _Cliente:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json):
            capturado["payload"] = json
            return _Respuesta()

    return _Cliente


@pytest.mark.asyncio
async def test_ollama_manda_num_predict_con_tope(monkeypatch):
    capturado = {}
    monkeypatch.setattr(llm.httpx, "AsyncClient", _cliente_que_captura(capturado))
    await llm._call_ollama("hola", model="m", timeout=5, max_tokens=512)
    assert capturado["payload"]["options"]["num_predict"] == 512


@pytest.mark.asyncio
async def test_ollama_sin_tope_no_manda_num_predict(monkeypatch):
    """Quien no pide tope no cambia de comportamiento."""
    capturado = {}
    monkeypatch.setattr(llm.httpx, "AsyncClient", _cliente_que_captura(capturado))
    await llm._call_ollama("hola", model="m", timeout=5)
    assert "num_predict" not in capturado["payload"].get("options", {})


# ── La síntesis del investigador pide tope ───────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("con_fuentes", [True, False])
async def test_la_sintesis_del_investigador_lleva_tope(monkeypatch, con_fuentes):
    async def rag_results(**kwargs):
        if not con_fuentes:
            return []
        return [{"text": "fragmento " * 50, "filename": "paper.pdf", "doc_id": "d1",
                 "doc_title": "Un paper", "doc_authors": "Autora"}]

    llamadas = []

    async def llm_falso(prompt, **kwargs):
        llamadas.append(kwargs)
        return "resumen " * 40

    async def backend(*args, **kwargs):
        return "qdrant"

    monkeypatch.setattr(adapter_investigador, "get_rag_backend", backend)
    estado = {
        "article_id": str(uuid.uuid4()),
        "project_id": str(uuid.uuid4()),
        "title": "harness engineering",
        "keywords": ["harness"],
        binding.CLAVE_ESTADO: binding.CapabilityBundle({"rag_results": rag_results, "llm": llm_falso}),
    }

    await adapter_investigador.run_investigador(estado)

    assert len(llamadas) == 1, "la síntesis debería llamar al LLM una vez"
    tope = llamadas[0].get("max_tokens")
    assert tope is not None and 0 < tope <= 2048, f"síntesis sin tope razonable: {tope!r}"
