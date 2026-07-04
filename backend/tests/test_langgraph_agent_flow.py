import asyncio
import uuid

import pytest

from app.modules.agents.application import use_cases as orquestador


@pytest.mark.asyncio
async def test_basic_langgraph_flow_monkeypatched_logs(monkeypatch):
    # Prevent DB logging side-effects by monkeypatching the log helpers
    async def noop_log_start(agent_name, article_id, author_id, input_payload):
        return uuid.uuid4()

    async def noop_log_end(run_id, output_payload, status, error_message=None):
        return None

    monkeypatch.setattr(orquestador, "log_run_start", noop_log_start)
    monkeypatch.setattr(orquestador, "log_run_end", noop_log_end)

    # Mock the LLM calls to avoid hitting local Ollama/OpenAI in tests
    import app.platform.llm
    import app.modules.agents.adapters.redactor as redactor_adapter
    import app.modules.agents.adapters.revisor as revisor_adapter

    async def mock_call_llm(prompt, **kwargs):
        if "revisor" in prompt.lower() or "reviewer" in prompt.lower():
            return '{"approval_score": 85, "feedback": ["Looks good but add details"]}'
        return "Resumen de investigacion o texto formateado."

    async def mock_call_llm_stream(prompt, **kwargs):
        tokens = ["# ", "Test ", "Draft ", "\n", "This ", "is ", "a ", "test ", "draft."]
        for token in tokens:
            yield token

    monkeypatch.setattr(app.platform.llm, "call_llm", mock_call_llm)
    monkeypatch.setattr(app.platform.llm, "call_llm_stream", mock_call_llm_stream)
    monkeypatch.setattr(redactor_adapter, "call_llm_stream", mock_call_llm_stream)
    monkeypatch.setattr(redactor_adapter, "call_llm", mock_call_llm)
    monkeypatch.setattr(revisor_adapter, "call_llm", mock_call_llm)

    # Use a small flow: investigador -> redactor -> revisor
    flow = ["investigador", "redactor", "revisor"]

    article_id = uuid.uuid4()
    author_id = uuid.uuid4()

    final_state = await orquestador.Orchestrator.run(
        article_id=article_id,
        author_id=author_id,
        title="Effects of local LLMs on scientific writing",
        keywords=["llm", "rag", "qdrant"],
        scientific_format="apa",
        flow_sequence=flow,
    )

    # Basic assertions: ensure final_state has expected keys
    assert isinstance(final_state, dict)
    assert "draft_text" in final_state or "research_data" in final_state
    # Approval score should be present (revisor sets it)
    assert "approval_score" in final_state
