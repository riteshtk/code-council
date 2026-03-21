"""Config endpoints — read, validate and update council configuration."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from codecouncil.config.loader import load_config

router = APIRouter(tags=["config"])

_MASKED = "***"
_SECRET_FIELDS = {"api_key", "github_token", "gitlab_token", "bitbucket_token"}


def _mask_secrets(data: Any) -> Any:
    """Recursively mask secret fields in a config dict."""
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if k in _SECRET_FIELDS and isinstance(v, str) and v:
                result[k] = _MASKED
            else:
                result[k] = _mask_secrets(v)
        return result
    if isinstance(data, list):
        return [_mask_secrets(item) for item in data]
    return data


@router.get("/config")
async def get_config() -> dict:
    """Return the merged active configuration with secrets masked."""
    cfg = load_config()
    raw = cfg.model_dump()
    return _mask_secrets(raw)


class ValidateConfigRequest(BaseModel):
    yaml_content: str


@router.post("/config/validate")
async def validate_config(body: ValidateConfigRequest) -> dict:
    """Validate a YAML config string. Returns errors if invalid."""
    try:
        data = yaml.safe_load(body.yaml_content)
        if not isinstance(data, dict):
            raise ValueError("Config must be a YAML mapping")
        load_config(overrides=data)
        return {"valid": True, "errors": []}
    except Exception as exc:
        return {"valid": False, "errors": [str(exc)]}


class PatchConfigRequest(BaseModel):
    overrides: dict[str, Any]


@router.patch("/config")
async def patch_config(body: PatchConfigRequest) -> dict:
    """Apply runtime overrides, persist to global config file, and return merged config."""
    try:
        cfg = load_config(overrides=body.overrides)

        # Persist to global config file so changes survive restarts
        config_dir = Path.home() / ".codecouncil"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.yaml"

        # Merge with existing config file if present
        existing: dict[str, Any] = {}
        if config_path.exists():
            with open(config_path) as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    existing = loaded

        existing.update(body.overrides)

        with open(config_path, "w") as f:
            yaml.dump(existing, f, default_flow_style=False)

        raw = cfg.model_dump()
        return _mask_secrets(raw)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
