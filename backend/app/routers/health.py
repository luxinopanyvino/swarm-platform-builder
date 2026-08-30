"""Liveness y readiness (SPEC-019 / T5.4 / AC4).

Son dos preguntas distintas y mezclarlas cuesta caro:

* **Liveness** (`/health`) — ¿sigue vivo el proceso? Si responde, el contenedor no
  hay que reiniciarlo. **No consulta dependencias a propósito**: si Postgres se cae
  y el liveness lo mirase, el orquestador reiniciaría el backend en bucle sin
  arreglar nada, y perdería las conexiones que sí funcionaban.
* **Readiness** (`/health/ready`) — ¿puede atender tráfico útil? Aquí sí se
  comprueban base de datos, Qdrant y el proveedor de LLM, y se devuelve **503 con el
  detalle de la que ha caído** para que el balanceador deje de mandarle peticiones
  mientras se recupera.

Ambos son públicos, porque quien los consulta es el orquestador y no tiene
credenciales. Por eso el detalle se limita a un estado por dependencia: ni URLs, ni
versiones, ni mensajes del motor, que serían un mapa de la infraestructura para
quien no debe tenerlo.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Literal

import httpx
from fastapi import APIRouter, Response
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.shared.qdrant import qdrant_headers

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

#: Los chequeos no pueden tardar más que el intervalo del healthcheck que los llama.
PROBE_TIMEOUT_SECONDS = 3.0

Status = Literal["ok", "error", "not_configured"]


async def _check_database() -> tuple[Status, str | None]:
    try:
        async with asyncio.timeout(PROBE_TIMEOUT_SECONDS):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        return "ok", None
    except Exception as exc:
        logger.warning(
            "Readiness: base de datos inalcanzable", exc_info=exc,
            extra={"event": "readiness_check_failed", "dependency": "database"},
        )
        return "error", "no alcanzable"


async def _check_qdrant() -> tuple[Status, str | None]:
    if not settings.QDRANT_URL:
        return "not_configured", None
    try:
        async with httpx.AsyncClient(
            base_url=settings.QDRANT_URL,
            timeout=PROBE_TIMEOUT_SECONDS,
            headers=qdrant_headers(),
        ) as client:
            response = await client.get("/healthz")
        if response.status_code >= 400:
            # Un 401/403 aquí es una API key mal configurada, no una caída: se
            # distingue porque el diagnóstico es completamente distinto.
            motivo = "credencial rechazada" if response.status_code in (401, 403) else "respuesta de error"
            return "error", motivo
        return "ok", None
    except Exception as exc:
        logger.warning(
            "Readiness: Qdrant inalcanzable", exc_info=exc,
            extra={"event": "readiness_check_failed", "dependency": "qdrant"},
        )
        return "error", "no alcanzable"


async def _check_llm() -> tuple[Status, str | None]:
    """Comprueba el proveedor **configurado**, que ya no es siempre Ollama.

    AC4 se escribió cuando Ollama era el único motor; desde E12 el proveedor por
    defecto es Anthropic. Con un proveedor remoto no se hace una llamada de prueba:
    costaría dinero en cada sondeo y el healthcheck se ejecuta cada pocos segundos.
    Se comprueba que haya credencial, que es la forma en que ese proveedor falla en
    la práctica. Con Ollama, que es local y gratuito, sí se sondea la red.
    """
    provider = (settings.LLM_PROVIDER or "").lower()

    if provider == "ollama":
        try:
            async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_SECONDS) as client:
                response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            return ("ok", None) if response.status_code < 400 else ("error", "respuesta de error")
        except Exception as exc:
            logger.warning(
                "Readiness: Ollama inalcanzable", exc_info=exc,
                extra={"event": "readiness_check_failed", "dependency": "llm"},
            )
            return "error", "no alcanzable"

    claves = {"anthropic": settings.ANTHROPIC_API_KEY, "openai": settings.OPENAI_API_KEY}
    if provider in claves:
        return ("ok", None) if claves[provider] else ("not_configured", "sin credencial")

    return "not_configured", "proveedor desconocido"


@router.get("/health")
async def liveness() -> dict:
    """¿Vive el proceso? Sin tocar dependencias (ver docstring del módulo)."""
    return {"status": "healthy", "service": "alejandria_backend"}


@router.get("/health/ready")
async def readiness(response: Response) -> dict:
    """¿Puede atender tráfico útil? `503` con el detalle de lo que falla."""
    (db_status, db_reason), (qdrant_status, qdrant_reason), (llm_status, llm_reason) = (
        # En paralelo: en serie, tres dependencias lentas sumarían sus tiempos de
        # espera y el sondeo tardaría más que el intervalo que lo invoca.
        await asyncio.gather(_check_database(), _check_qdrant(), _check_llm())
    )

    checks = {
        "database": {"status": db_status},
        "qdrant": {"status": qdrant_status},
        "llm": {"status": llm_status, "provider": (settings.LLM_PROVIDER or "").lower()},
    }
    for nombre, motivo in (("database", db_reason), ("qdrant", qdrant_reason), ("llm", llm_reason)):
        if motivo:
            checks[nombre]["reason"] = motivo

    listo = all(check["status"] == "ok" for check in checks.values())
    if not listo:
        response.status_code = 503
        logger.warning(
            "Readiness: no listo para recibir tráfico",
            extra={
                "event": "readiness_not_ready",
                "failing": [n for n, c in checks.items() if c["status"] != "ok"],
            },
        )

    return {"status": "ready" if listo else "not_ready", "checks": checks}
