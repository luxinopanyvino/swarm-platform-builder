"""Verify a failed pipeline resumes from its last checkpoint instead of restarting."""
import uuid

import pytest

from app.modules.agents.application import use_cases as orquestador
from app.shared.llm import TransientLLMError


@pytest.mark.asyncio
async def test_resume_from_checkpoint_preserves_completed_nodes(monkeypatch):
    # Avoid DB side-effects from run logging
    async def noop_log_start(agent_name, article_id, author_id, input_payload):
        return uuid.uuid4()

    async def noop_log_end(run_id, output_payload, status, error_message=None):
        return None

    monkeypatch.setattr(orquestador, "log_run_start", noop_log_start)
    monkeypatch.setattr(orquestador, "log_run_end", noop_log_end)

    # Count how many times each node actually executes
    calls = {"investigador": 0, "redactor": 0}

    async def fake_investigador(state):
        calls["investigador"] += 1
        return {"research_data": "datos de investigacion"}

    fail_once = {"done": False}

    async def fake_redactor(state):
        calls["redactor"] += 1
        if not fail_once["done"]:
            fail_once["done"] = True
            raise RuntimeError("Ollama stream unavailable: All connection attempts failed")
        # On resume the research_data from the completed investigador must still be present
        assert state.get("research_data") == "datos de investigacion"
        return {"draft_text": "# Borrador\nContenido"}

    monkeypatch.setattr(orquestador, "run_investigador", fake_investigador)
    monkeypatch.setattr(orquestador, "run_redactor", fake_redactor)

    flow = ["investigador", "redactor"]
    article_id = uuid.uuid4()
    author_id = uuid.uuid4()

    # First attempt fails at redactor
    with pytest.raises(RuntimeError):
        await orquestador.Orchestrator.run(
            article_id=article_id,
            author_id=author_id,
            title="Test resume",
            keywords=["x"],
            scientific_format="apa",
            flow_sequence=flow,
        )

    # A resumable checkpoint must now exist
    assert await orquestador.has_pipeline_checkpoint(article_id) is True

    # Resume — should NOT re-run investigador, only retry redactor
    final_state = await orquestador.Orchestrator.run(
        article_id=article_id,
        author_id=author_id,
        title="Test resume",
        keywords=["x"],
        scientific_format="apa",
        flow_sequence=flow,
        resume=True,
    )

    assert calls["investigador"] == 1, "investigador should not re-run on resume"
    assert calls["redactor"] == 2, "redactor should run once (fail) then once (resume)"
    assert final_state["draft_text"] == "# Borrador\nContenido"
    assert final_state["research_data"] == "datos de investigacion"

    # Checkpoint cleaned up after a successful completion
    assert await orquestador.has_pipeline_checkpoint(article_id) is False


@pytest.mark.asyncio
async def test_transient_failure_auto_resumes_without_user(monkeypatch):
    """A transient node failure auto-resumes from the checkpoint and completes."""
    async def noop_log_start(agent_name, article_id, author_id, input_payload):
        return uuid.uuid4()

    async def noop_log_end(run_id, output_payload, status, error_message=None):
        return None

    monkeypatch.setattr(orquestador, "log_run_start", noop_log_start)
    monkeypatch.setattr(orquestador, "log_run_end", noop_log_end)

    # Make auto-resume immediate so the test doesn't sleep
    from app.core import config
    monkeypatch.setattr(config.settings, "PIPELINE_AUTO_RESUME_ATTEMPTS", 2, raising=False)
    monkeypatch.setattr(config.settings, "PIPELINE_AUTO_RESUME_DELAY", 0.0, raising=False)

    calls = {"investigador": 0, "redactor": 0}

    async def fake_investigador(state):
        calls["investigador"] += 1
        return {"research_data": "datos"}

    fail_once = {"done": False}

    async def fake_redactor(state):
        calls["redactor"] += 1
        if not fail_once["done"]:
            fail_once["done"] = True
            raise TransientLLMError("Ollama stream unavailable: All connection attempts failed")
        return {"draft_text": "# Borrador"}

    monkeypatch.setattr(orquestador, "run_investigador", fake_investigador)
    monkeypatch.setattr(orquestador, "run_redactor", fake_redactor)

    article_id = uuid.uuid4()
    # No exception should escape — the orchestrator auto-resumes and finishes
    final_state = await orquestador.Orchestrator.run(
        article_id=article_id,
        author_id=uuid.uuid4(),
        title="Auto resume",
        keywords=["x"],
        scientific_format="apa",
        flow_sequence=["investigador", "redactor"],
    )

    assert calls["investigador"] == 1   # not re-run on auto-resume
    assert calls["redactor"] == 2       # failed once, auto-resumed, succeeded
    assert final_state["draft_text"] == "# Borrador"


@pytest.mark.asyncio
async def test_permanent_failure_is_not_auto_resumed(monkeypatch):
    """A permanent (non-transient) error surfaces immediately without auto-resume loops."""
    async def noop_log_start(agent_name, article_id, author_id, input_payload):
        return uuid.uuid4()

    async def noop_log_end(run_id, output_payload, status, error_message=None):
        return None

    monkeypatch.setattr(orquestador, "log_run_start", noop_log_start)
    monkeypatch.setattr(orquestador, "log_run_end", noop_log_end)

    from app.core import config
    monkeypatch.setattr(config.settings, "PIPELINE_AUTO_RESUME_ATTEMPTS", 2, raising=False)
    monkeypatch.setattr(config.settings, "PIPELINE_AUTO_RESUME_DELAY", 0.0, raising=False)

    calls = {"redactor": 0}

    async def fake_investigador(state):
        return {"research_data": "datos"}

    async def fake_redactor(state):
        calls["redactor"] += 1
        raise RuntimeError("Ollama returned HTTP 404: model not found")  # permanent

    monkeypatch.setattr(orquestador, "run_investigador", fake_investigador)
    monkeypatch.setattr(orquestador, "run_redactor", fake_redactor)

    article_id = uuid.uuid4()
    with pytest.raises(RuntimeError):
        await orquestador.Orchestrator.run(
            article_id=article_id,
            author_id=uuid.uuid4(),
            title="Permanent",
            keywords=["x"],
            scientific_format="apa",
            flow_sequence=["investigador", "redactor"],
        )

    assert calls["redactor"] == 1  # ran once, no auto-resume retries

    # Clean up the leftover checkpoint so it doesn't leak into other tests
    await orquestador._pipeline_checkpointer.adelete_thread(str(article_id))
