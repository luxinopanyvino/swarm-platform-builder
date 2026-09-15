"""Modelos con razonamiento en Ollama (qwen3.5, olmo-3…).

Desde Ollama 0.9 el razonamiento llega aparte, en `thinking`, y `response` va
vacío mientras el modelo piensa. Con `qwen3.5:4b` y el `num_ctx=4096` del redactor,
el modelo gastaba el contexto pensando y terminaba por `length` sin escribir nada:
«LLM devolvió una respuesta vacía al generar el borrador».
"""
import json

import pytest

import app.platform.llm as llm
from app.core import config
from app.platform.llm import TransientLLMError


@pytest.fixture(autouse=True)
def _ollama_sin_esperas(monkeypatch):
    monkeypatch.setattr(llm, "_retry_params", lambda: (3, 0.0, 0.0))
    monkeypatch.setattr(config.settings, "LLM_PROVIDER", "ollama", raising=False)


# ── Dobles de httpx ──────────────────────────────────────────────────────────

class _Respuesta:
    status_code = 200
    text = ""

    def __init__(self, datos):
        self._datos = datos

    def json(self):
        return self._datos


class _Stream:
    status_code = 200

    def __init__(self, chunks):
        self._chunks = chunks

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def aiter_lines(self):
        for chunk in self._chunks:
            yield json.dumps(chunk)


def _cliente(capturado, *, datos=None, chunks=None):
    class _Cliente:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json):
            capturado.setdefault("payloads", []).append(json)
            return _Respuesta(datos)

        def stream(self, method, url, json):
            capturado.setdefault("payloads", []).append(json)
            return _Stream(chunks)

    return _Cliente


# ── Sin streaming ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_pide_no_razonar(monkeypatch):
    capturado = {}
    monkeypatch.setattr(llm.httpx, "AsyncClient", _cliente(capturado, datos={"response": "hola"}))
    assert await llm._call_ollama("hola", model="m", timeout=5) == "hola"
    assert capturado["payloads"][0]["think"] is False


@pytest.mark.asyncio
async def test_solo_razonamiento_es_un_error_claro_y_no_se_reintenta(monkeypatch):
    capturado = {}
    datos = {"response": "", "thinking": "Primero pienso que…", "done_reason": "length"}
    monkeypatch.setattr(llm.httpx, "AsyncClient", _cliente(capturado, datos=datos))

    with pytest.raises(RuntimeError) as error:
        await llm.call_llm("hola", model="olmo-3:7b", num_ctx=4096)

    assert not isinstance(error.value, TransientLLMError)
    assert "razonamiento" in str(error.value) and "num_ctx=4096" in str(error.value)
    assert len(capturado["payloads"]) == 1, "con el mismo contexto volvería a pasar"


@pytest.mark.asyncio
async def test_vacia_sin_razonamiento_sigue_siendo_transitoria(monkeypatch):
    """El caso de siempre (modelo calentando) no cambia: se reintenta."""
    capturado = {}
    monkeypatch.setattr(llm.httpx, "AsyncClient", _cliente(capturado, datos={"response": ""}))
    with pytest.raises(TransientLLMError):
        await llm.call_llm("hola", model="m")
    assert len(capturado["payloads"]) == 4


# ── Streaming (el redactor) ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stream_pide_no_razonar_y_emite_la_respuesta(monkeypatch):
    capturado = {}
    chunks = [{"response": "Hola"}, {"response": " mundo"}, {"done": True, "done_reason": "stop"}]
    monkeypatch.setattr(llm.httpx, "AsyncClient", _cliente(capturado, chunks=chunks))

    tokens = [t async for t in llm.call_llm_stream("hola", model="qwen3.5:4b")]

    assert "".join(tokens) == "Hola mundo"
    assert capturado["payloads"][0]["think"] is False


@pytest.mark.asyncio
async def test_stream_solo_razonamiento_falla_con_motivo_y_sin_reintento(monkeypatch):
    capturado = {}
    chunks = [
        {"response": "", "thinking": "Voy a estructurar"},
        {"response": "", "thinking": " el artículo…"},
        {"response": "", "done": True, "done_reason": "length"},
    ]
    monkeypatch.setattr(llm.httpx, "AsyncClient", _cliente(capturado, chunks=chunks))

    with pytest.raises(RuntimeError) as error:
        [t async for t in llm.call_llm_stream("hola", model="qwen3.5:4b", num_ctx=4096)]

    assert not isinstance(error.value, TransientLLMError)
    assert "agotó la ventana" in str(error.value)
    assert len(capturado["payloads"]) == 1


@pytest.mark.asyncio
async def test_stream_con_razonamiento_y_respuesta_no_falla(monkeypatch):
    """Un modelo que piensa y luego responde es válido: solo falla si no responde."""
    capturado = {}
    chunks = [{"thinking": "mmm"}, {"response": "Texto"}, {"done": True, "done_reason": "stop"}]
    monkeypatch.setattr(llm.httpx, "AsyncClient", _cliente(capturado, chunks=chunks))
    assert "".join([t async for t in llm.call_llm_stream("hola", model="olmo-3:7b")]) == "Texto"
