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
