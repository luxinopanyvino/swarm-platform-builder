"""Config router: read/write config.yaml visually."""
import yaml
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from app.routers.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/v1/config", tags=["config"])


def get_config_path() -> Path:
    # Try different locations based on current working directory
    paths = [
        Path("config.yaml"),
        Path("../config.yaml"),
        Path("../../config.yaml"),
        Path("backend/config.yaml"),
    ]
    for p in paths:
        if p.exists() and p.is_file() and p.stat().st_size > 0:
            return p
    # Fallback to the first existing config.yaml
    for p in paths:
        if p.exists():
            return p
    return Path("config.yaml")


@router.get("")
async def get_config(token_data=Depends(get_current_user)):
    """Retrieve current YAML configuration as JSON."""
    path = get_config_path()
    if not path.exists():
        raise HTTPException(status_code=404, detail="config.yaml not found")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read config: {str(e)}")


@router.get("/llm-status")
async def get_llm_status(token_data=Depends(get_current_user)):
    """Effective LLM engine status, resolved through the full config precedence.

    Deliberately returns **no key material** — only whether each provider's
    credential is present. The UI uses this to *report* that ANTHROPIC_API_KEY
    is set instead of offering a field that would write the secret into
    config.yaml, which is tracked in git (SPEC-023).

    Kept out of ``GET /config`` on purpose: that payload is echoed back to
    ``PUT /config`` and written verbatim to the YAML, so injecting computed
    fields there would persist them into the file.
    """
    from app.core.config import settings

    return {
        "provider": settings.LLM_PROVIDER,
        "anthropic": {
            "api_key_set": bool(settings.ANTHROPIC_API_KEY),
            "model": settings.ANTHROPIC_MODEL,
        },
        "openai": {"api_key_set": bool(settings.OPENAI_API_KEY)},
    }


@router.put("")
async def update_config(data: dict, token_data=Depends(require_admin)):
    """Overwrite YAML configuration with new JSON values."""
    path = get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

        # Sync with other possible locations
        alt_paths = [
            Path("config.yaml"),
            Path("../config.yaml"),
            Path("backend/config.yaml"),
        ]
        for p in alt_paths:
            if p.exists() and p.resolve() != path.resolve():
                with open(p, "w", encoding="utf-8") as f:
                    yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

        return {"status": "success", "message": "Configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")
