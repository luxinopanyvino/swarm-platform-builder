import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel


class Settings(BaseModel):
    """Configuracion global de la aplicacion."""

    # Core
    APP_NAME: str = "Alejandria Magazine"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/alejandria"

    # Security
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Brute-force / credential-stuffing protection for the auth endpoints.
    # Sliding-window rate limit per client IP (login & register) and per-account
    # lockout after consecutive failed logins.
    AUTH_RATELIMIT_MAX_ATTEMPTS: int = 10      # attempts per window per IP (0 disables)
    AUTH_RATELIMIT_WINDOW_SECONDS: int = 60    # rolling window length, seconds
    AUTH_LOCKOUT_MAX_FAILED: int = 5           # failed logins before lockout (0 disables)
    AUTH_LOCKOUT_SECONDS: int = 900            # lockout duration, seconds (15 min)

    # Access controls — MUST be False in production
    ENABLE_DEV_ROLE_PROMOTION: bool = False

    # Default role assigned to users who self-register. Minimal privilege by
    # design: only "lector" or "publico" are accepted; anything else falls back
    # to "lector". Never grant "redactor"/"admin" on signup.
    DEFAULT_SIGNUP_ROLE: str = "lector"

    # Redis
    REDIS_URL: str = "redis://:password@localhost:6379/0"

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:1b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION: str = "rag_docs"
    RAG_VECTOR_SIZE: int = 768

    # LLM Provider — "ollama" (default, on-prem) | "openai" (OpenAI-compatible API)
    LLM_PROVIDER: str = "ollama"

    # LLM resilience — automatic retry of transient failures (connection refused,
    # timeouts, 5xx, empty responses) with exponential backoff + jitter.
    LLM_MAX_RETRIES: int = 3          # extra attempts after the first try (0 disables)
    LLM_RETRY_BASE_DELAY: float = 1.0  # seconds; first backoff, doubles each retry
    LLM_RETRY_MAX_DELAY: float = 10.0  # cap for a single backoff wait

    # Pipeline auto-resume — when a node fails with a transient error even after the
    # LLM retries above, the orchestrator resumes from the last checkpoint this many
    # times (with backoff) before surfacing the failure for a manual retry.
    PIPELINE_AUTO_RESUME_ATTEMPTS: int = 2
    PIPELINE_AUTO_RESUME_DELAY: float = 3.0

    # OpenAI / OpenAI-compatible (Azure, vLLM, Groq, etc.)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBED_MODEL: str = "text-embedding-3-small"
    # Override to use Azure OpenAI, vLLM compat layer, Groq, etc.
    # Leave empty to use the official OpenAI endpoint.
    OPENAI_BASE_URL: Optional[str] = None

    # Investigador scraper
    SCRAPER_SEMANTIC_RERANK: bool = True
    # Egress allowlist for outbound scraper/robots fetches (SSRF guard, SPEC-002).
    # Empty = allow any public destination; non-empty = only these domains (and
    # their subdomains) are permitted. Comma-separated when set via env var.
    SCRAPER_ALLOWED_DOMAINS: list[str] = []

    # RAG global defaults
    RAG_CHUNK_SIZE: int = 800
    RAG_CHUNK_OVERLAP: int = 80
    RAG_TOP_K: int = 6
    RAG_SCORE_THRESHOLD: float = 0.0

    # MinIO
    MINIO_URL: str = "http://localhost:9000"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin"


def _to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _read_yaml_config() -> dict[str, Any]:
    configured = os.getenv("CONFIG_YAML_PATH", "").strip()
    candidates = []
    if configured:
        candidates.append(Path(configured))
    candidates.extend(
        [
            Path("config.yaml"),
            Path("../config.yaml"),
            Path("../../config.yaml"),
        ]
    )

    for candidate in candidates:
        if candidate.exists():
            with candidate.open("r", encoding="utf-8") as file:
                return yaml.safe_load(file) or {}
    return {}


def _build_settings() -> Settings:
    yaml_config = _read_yaml_config()

    app = yaml_config.get("app", {})
    security = yaml_config.get("security", {})
    access = yaml_config.get("access_control", {})
    database = yaml_config.get("database", {})
    redis = yaml_config.get("redis", {})
    ollama = yaml_config.get("ollama", {})
    qdrant = yaml_config.get("qdrant", {})
    minio = yaml_config.get("minio", {})

    merged: dict[str, Any] = {
        "APP_NAME": app.get("name", "Alejandria Magazine"),
        "VERSION": app.get("version", "0.1.0"),
        "DEBUG": app.get("debug", False),
        "DATABASE_URL": database.get(
            "url", "postgresql+asyncpg://postgres:password@localhost:5432/alejandria"
        ),
        "SECRET_KEY": security.get("secret_key", "your-secret-key-change-in-production"),
        "ALGORITHM": security.get("algorithm", "HS256"),
        "ACCESS_TOKEN_EXPIRE_MINUTES": security.get("access_token_expire_minutes", 30),
        "REFRESH_TOKEN_EXPIRE_DAYS": security.get("refresh_token_expire_days", 7),
        "AUTH_RATELIMIT_MAX_ATTEMPTS": security.get("auth_ratelimit_max_attempts", 10),
        "AUTH_RATELIMIT_WINDOW_SECONDS": security.get("auth_ratelimit_window_seconds", 60),
        "AUTH_LOCKOUT_MAX_FAILED": security.get("auth_lockout_max_failed", 5),
        "AUTH_LOCKOUT_SECONDS": security.get("auth_lockout_seconds", 900),
        # Fail-safe: when the key is absent the effective value is False.
        "ENABLE_DEV_ROLE_PROMOTION": access.get("enable_dev_role_promotion", False),
        "DEFAULT_SIGNUP_ROLE": access.get("default_signup_role", "lector"),
        "REDIS_URL": redis.get("url", "redis://:password@localhost:6379/0"),
        "OLLAMA_BASE_URL": ollama.get("base_url", "http://localhost:11434"),
        "OLLAMA_MODEL": ollama.get("default_model", "llama3.2:1b"),
        "OLLAMA_EMBED_MODEL": ollama.get("embed_model", "nomic-embed-text"),
        "QDRANT_URL": qdrant.get("url", "http://localhost:6333"),
        "QDRANT_API_KEY": qdrant.get("api_key"),
        "QDRANT_COLLECTION": qdrant.get("collection", "rag_docs"),
        "RAG_VECTOR_SIZE": qdrant.get("vector_size", 768),
        "MINIO_URL": minio.get("url", "http://localhost:9000"),
        "MINIO_ROOT_USER": minio.get("root_user", "minioadmin"),
        "MINIO_ROOT_PASSWORD": minio.get("root_password", "minioadmin"),
        # LLM provider
        "LLM_PROVIDER": yaml_config.get("llm", {}).get("provider", "ollama"),
        "LLM_MAX_RETRIES": yaml_config.get("llm", {}).get("max_retries", 3),
        "LLM_RETRY_BASE_DELAY": yaml_config.get("llm", {}).get("retry_base_delay", 1.0),
        "LLM_RETRY_MAX_DELAY": yaml_config.get("llm", {}).get("retry_max_delay", 10.0),
        "PIPELINE_AUTO_RESUME_ATTEMPTS": yaml_config.get("llm", {}).get("auto_resume_attempts", 2),
        "PIPELINE_AUTO_RESUME_DELAY": yaml_config.get("llm", {}).get("auto_resume_delay", 3.0),
        "OPENAI_API_KEY": yaml_config.get("openai", {}).get("api_key", ""),
        "OPENAI_MODEL": yaml_config.get("openai", {}).get("model", "gpt-4o-mini"),
        "OPENAI_EMBED_MODEL": yaml_config.get("openai", {}).get("embed_model", "text-embedding-3-small"),
        "OPENAI_BASE_URL": yaml_config.get("openai", {}).get("base_url") or None,
        # Investigador scraper — reads from agents.investigador first, then legacy investigador key
        "SCRAPER_SEMANTIC_RERANK": (
            yaml_config.get("agents", {}).get("investigador", {}).get("semantic_rerank")
            if yaml_config.get("agents", {}).get("investigador", {}).get("semantic_rerank") is not None
            else yaml_config.get("investigador", {}).get("semantic_rerank", True)
        ),
        "SCRAPER_ALLOWED_DOMAINS": (
            yaml_config.get("agents", {}).get("investigador", {}).get("allowed_domains")
            or yaml_config.get("investigador", {}).get("allowed_domains")
            or []
        ),
        # RAG global defaults
        "RAG_CHUNK_SIZE": yaml_config.get("rag", {}).get("chunk_size", 800),
        "RAG_CHUNK_OVERLAP": yaml_config.get("rag", {}).get("chunk_overlap", 80),
        "RAG_TOP_K": yaml_config.get("rag", {}).get("top_k", 6),
        "RAG_SCORE_THRESHOLD": yaml_config.get("rag", {}).get("score_threshold", 0.0),
    }

    # Environment variables override config.yaml
    for key in list(merged.keys()):
        env_value = os.getenv(key)
        if env_value is None:
            continue
        if isinstance(merged[key], bool):
            merged[key] = _to_bool(env_value)
        elif isinstance(merged[key], list):
            merged[key] = [item.strip() for item in env_value.split(",") if item.strip()]
        elif isinstance(merged[key], int):
            merged[key] = int(env_value)
        else:
            merged[key] = env_value

    return Settings(**merged)


def _validate_settings(s: Settings) -> None:
    """Fail fast on insecure production configurations."""
    insecure_defaults = {"", "your-secret-key-change-in-production", "local-dev-secret", "local-dev-secret-key-not-for-production"}
    if not s.DEBUG and s.SECRET_KEY in insecure_defaults:
        raise ValueError(
            "SECRET_KEY must be set to a strong random value in production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )


settings = _build_settings()
_validate_settings(settings)
