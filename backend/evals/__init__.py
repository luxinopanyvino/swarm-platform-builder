"""Evaluation harnesses for the platform.

Two distinct, non-overlapping efforts live under this package (see ADR-0006
and SPEC-025 for the boundary between them):

- ``model_benchmark/`` — one-off comparison of *foundation* open-source models
  (which base model is best for each agent role) — SPEC-025 / epic E13.
- Agent-behavior EDD evals (SPEC-014 / epic E9) — evaluate the configured
  agents' behavior over time, not foundation models. Lives alongside this
  package once implemented (T9.3).
"""
