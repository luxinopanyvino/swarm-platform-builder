"""Model benchmark harness — SPEC-025 / epic E13 (T13.1).

Compares candidate open-source foundation models (run locally via Ollama)
across the four real agent roles of the AlejandrIA Magazine pipeline
(investigador, redactor, revisor, formateador), on reasoning/quality and on
compute cost (latency, throughput, RAM/VRAM).

Out of scope (see ADR-0006 / SPEC-014): evaluating the *behavior* of agents
already configured in production — that is the EDD harness's job, not this
one's. This package only helps pick the foundation model in the first place.
"""
