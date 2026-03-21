"""
7-layer config loader for CodeCouncil.

Merge order (later layers win):
  1. Built-in defaults  (CouncilConfig())
  2. Global config      (~/.codecouncil/config.yaml  or  global_path)
  3. Project config     (.codecouncil.yaml in cwd    or  project_path)
  4. Runtime config     (config_path argument)
  5. Environment vars   (CC_ prefix, __ as nested separator)
  6. API overrides      (overrides dict argument)

Helper: deep_merge(base, override) — recursively merges dicts without
        clobbering sibling keys.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from codecouncil.config.schema import CouncilConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively merge *override* into *base*, returning a new dict.

    - dict values are merged recursively.
    - All other types (list, scalar) in override replace the base value.
    """
    result: dict[str, Any] = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_yaml_file(path: str | Path) -> dict[str, Any]:
    """Load a YAML file, returning an empty dict if the file does not exist."""
    try:
        with open(path) as fh:
            data = yaml.safe_load(fh)
            return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def _env_to_nested(prefix: str = "CC_") -> dict[str, Any]:
    """
    Collect environment variables that start with *prefix* and convert them
    to a nested dict using ``__`` as the level separator.

    Example:
        CC_COUNCIL__MAX_ROUNDS=7  →  {"council": {"max_rounds": 7}}
        CC_LLM__DEFAULT_PROVIDER=anthropic  →  {"llm": {"default_provider": "anthropic"}}

    Values are kept as strings; Pydantic will coerce them to the right type
    when the model is constructed.
    """
    result: dict[str, Any] = {}
    prefix_len = len(prefix)

    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue

        # Strip prefix, lowercase, split on double-underscore
        stripped = key[prefix_len:].lower()
        parts = stripped.split("__")

        # Navigate/build nested dicts
        node = result
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = _coerce_env_value(value)

    return result


def _coerce_env_value(value: str) -> Any:
    """
    Attempt to coerce a string env-var value to bool, int, or float.
    Falls back to the raw string.
    """
    # Boolean
    if value.lower() in ("true", "yes", "1"):
        return True
    if value.lower() in ("false", "no", "0"):
        return False
    # Integer
    try:
        return int(value)
    except ValueError:
        pass
    # Float
    try:
        return float(value)
    except ValueError:
        pass
    return value


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_config(
    global_path: str | None = None,
    project_path: str | None = None,
    config_path: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> CouncilConfig:
    """
    Build a ``CouncilConfig`` by merging configuration from 6 layers in order.

    Parameters
    ----------
    global_path:
        Explicit path to a global config YAML.  Defaults to
        ``~/.codecouncil/config.yaml``.
    project_path:
        Explicit path to a project config YAML.  Defaults to
        ``.codecouncil.yaml`` in the current working directory.
    config_path:
        Path to a runtime/one-off config YAML (e.g. passed via CLI ``--config``).
    overrides:
        A dict of raw config values injected at the highest priority layer
        (e.g. from the REST API or programmatic callers).

    Returns
    -------
    CouncilConfig
        A fully validated, merged configuration object.
    """
    # Layer 1 — built-in defaults
    merged: dict[str, Any] = CouncilConfig().model_dump()

    # Layer 2 — global config
    _global = global_path or str(Path.home() / ".codecouncil" / "config.yaml")
    merged = deep_merge(merged, _load_yaml_file(_global))

    # Layer 3 — project config
    _project = project_path or str(Path.cwd() / ".codecouncil.yaml")
    merged = deep_merge(merged, _load_yaml_file(_project))

    # Layer 4 — runtime config (explicit config_path)
    if config_path:
        merged = deep_merge(merged, _load_yaml_file(config_path))

    # Layer 5 — environment variables (CC_ prefix)
    merged = deep_merge(merged, _env_to_nested("CC_"))

    # Layer 6 — API / programmatic overrides
    if overrides:
        merged = deep_merge(merged, overrides)

    return CouncilConfig.model_validate(merged)
