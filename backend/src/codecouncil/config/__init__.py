"""
CodeCouncil config package.

Public API:
    load_config()   — build a merged CouncilConfig from all layers
    CouncilConfig   — root Pydantic model
    deep_merge()    — utility for merging config dicts
"""
from codecouncil.config.loader import load_config
from codecouncil.config.schema import (
    AgentConfig,
    AgentsSettings,
    CouncilConfig,
    CouncilSettings,
    IngestConfig,
    LLMSettings,
    OutputConfig,
    ProviderConfig,
    UIConfig,
)

__all__ = [
    "load_config",
    "CouncilConfig",
    "CouncilSettings",
    "LLMSettings",
    "ProviderConfig",
    "AgentConfig",
    "AgentsSettings",
    "IngestConfig",
    "OutputConfig",
    "UIConfig",
]
