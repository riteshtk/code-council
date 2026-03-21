"""
Pydantic v2 models for all CodeCouncil configuration.

Every section of config is represented as a typed, validated model.
The root model is CouncilConfig which composes all sections.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Council-level settings
# ---------------------------------------------------------------------------

DebateTopology = Literal[
    "adversarial",
    "collaborative",
    "socratic",
    "open_floor",
    "panel",
    "custom",
]


class CouncilSettings(BaseModel):
    name: str = "Default Council"
    max_rounds: int = 3
    parallel_analysis: bool = True
    debate_topology: DebateTopology = "adversarial"
    custom_topology: list[str] = Field(default_factory=list)
    vote_threshold: float = Field(default=0.5, ge=0, le=1)
    vote_threshold_critical: float = Field(default=1.0, ge=0, le=1)
    deadlock_detection: bool = True
    hitl_enabled: bool = False
    hitl_timeout_minutes: int = 30
    budget_limit_usd: float = 0
    session_memory: bool = True


# ---------------------------------------------------------------------------
# LLM provider settings
# ---------------------------------------------------------------------------

class ProviderConfig(BaseModel):
    api_key: str = ""
    base_url: str = ""
    org_id: str = ""
    region: str = "us-east-1"
    profile: str = ""
    endpoint: str = ""
    api_version: str = "2024-02-01"


class LLMSettings(BaseModel):
    default_provider: str = "openai"
    default_model: str = "gpt-4o"
    providers: dict[str, ProviderConfig] = Field(
        default_factory=lambda: {
            "openai": ProviderConfig(),
            "anthropic": ProviderConfig(),
            "google": ProviderConfig(),
            "mistral": ProviderConfig(),
            "ollama": ProviderConfig(),
            "bedrock": ProviderConfig(),
            "azure": ProviderConfig(),
        }
    )


# ---------------------------------------------------------------------------
# Base agent config
# ---------------------------------------------------------------------------

class AgentConfig(BaseModel):
    enabled: bool = True
    provider: str = ""
    model: str = ""
    temperature: float = 0.5
    max_tokens: int = 2000
    streaming: bool = True
    persona: str = "default"
    vote_weight: float = Field(default=1.0, ge=0)
    focus_areas: dict[str, bool] = Field(default_factory=dict)
    thresholds: dict[str, float] = Field(default_factory=dict)
    fallback_providers: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Per-agent configs
# ---------------------------------------------------------------------------

class ArchaeologistConfig(AgentConfig):
    temperature: float = 0.3
    max_tokens: int = 2000
    focus_areas: dict[str, bool] = Field(
        default_factory=lambda: {
            "git_history": True,
            "churn_analysis": True,
            "bus_factor": True,
            "dead_code": True,
            "test_coverage": True,
        }
    )
    thresholds: dict[str, float] = Field(
        default_factory=lambda: {
            "churn_high": 0.7,
            "coverage_low": 0.4,
            "bus_factor_critical": 1.5,
        }
    )


class SkepticConfig(AgentConfig):
    temperature: float = 0.2
    max_tokens: int = 2000
    can_deadlock: bool = True
    deadlock_requires_evidence: bool = True
    focus_areas: dict[str, bool] = Field(
        default_factory=lambda: {
            "security": True,
            "performance": True,
            "scalability": True,
            "coupling": True,
            "tech_debt": True,
        }
    )
    thresholds: dict[str, float] = Field(
        default_factory=lambda: {
            "severity_deadlock": 0.9,
            "severity_veto": 0.75,
        }
    )


class VisionaryConfig(AgentConfig):
    temperature: float = 0.7
    max_tokens: int = 2500
    max_proposals: int = 8
    ambition_level: Literal["conservative", "moderate", "ambitious"] = "moderate"
    focus_areas: dict[str, bool] = Field(
        default_factory=lambda: {
            "architecture": True,
            "modernization": True,
            "developer_experience": True,
            "observability": True,
            "automation": True,
        }
    )
    thresholds: dict[str, float] = Field(
        default_factory=lambda: {
            "min_impact_score": 0.3,
            "effort_ceiling": 0.9,
        }
    )


class ScribeConfig(AgentConfig):
    temperature: float = 0.1
    max_tokens: int = 4000
    output_format: Literal["markdown", "json", "html"] = "markdown"
    preserve_dissent: bool = True
    include_debate_excerpt: bool = True
    excerpt_max_exchanges: int = 5
    action_item_format: Literal["numbered", "bulleted", "table"] = "numbered"
    rfc_sections: dict[str, bool] = Field(
        default_factory=lambda: {
            "executive_summary": True,
            "findings": True,
            "proposals": True,
            "debate_summary": True,
            "action_items": True,
            "dissent": True,
            "appendix": True,
        }
    )
    focus_areas: dict[str, bool] = Field(
        default_factory=lambda: {
            "synthesis": True,
            "action_items": True,
            "dissent_capture": True,
            "rfc_structure": True,
        }
    )


# ---------------------------------------------------------------------------
# Custom agent
# ---------------------------------------------------------------------------

class CustomAgentConfig(AgentConfig):
    name: str = ""
    role: str = ""


# ---------------------------------------------------------------------------
# Agents aggregator
# ---------------------------------------------------------------------------

class AgentsSettings(BaseModel):
    archaeologist: ArchaeologistConfig = Field(default_factory=ArchaeologistConfig)
    skeptic: SkepticConfig = Field(default_factory=SkepticConfig)
    visionary: VisionaryConfig = Field(default_factory=VisionaryConfig)
    scribe: ScribeConfig = Field(default_factory=ScribeConfig)
    custom: list[CustomAgentConfig] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Ingestion config
# ---------------------------------------------------------------------------

class IngestConfig(BaseModel):
    source: str = "github_api"
    github_token: str = ""
    gitlab_token: str = ""
    bitbucket_token: str = ""
    max_files: int = 500
    max_file_size_kb: int = 100
    git_log_limit: int = 200
    ast_parse: bool = True
    dependency_scan: bool = True
    cve_scan: bool = True
    secret_detection: bool = True
    licence_check: bool = True
    incremental: bool = True
    include_extensions: list[str] = Field(
        default_factory=lambda: [
            ".py",
            ".js",
            ".ts",
            ".tsx",
            ".jsx",
            ".go",
            ".rs",
            ".java",
            ".kt",
            ".rb",
            ".php",
            ".cs",
            ".cpp",
            ".c",
            ".h",
            ".yaml",
        ]
    )
    exclude_paths: list[str] = Field(
        default_factory=lambda: [
            "node_modules",
            ".git",
            "dist",
            "build",
            "__pycache__",
        ]
    )


# ---------------------------------------------------------------------------
# Output config
# ---------------------------------------------------------------------------

class OutputConfig(BaseModel):
    directory: str = "./output"
    filename_pattern: str = "RFC-{repo}-{timestamp}"
    formats: list[str] = Field(default_factory=lambda: ["markdown"])
    save_debate_transcript: bool = True
    save_agent_events: bool = True
    save_cost_report: bool = True
    save_state_snapshots: bool = False
    open_after_complete: bool = True
    webhook_url: str = ""


# ---------------------------------------------------------------------------
# UI config
# ---------------------------------------------------------------------------

class UIConfig(BaseModel):
    api_port: int = 8000
    ui_port: int = 5173
    theme: Literal["dark", "light", "system"] = "dark"
    stream_delay_ms: int = 0
    show_agent_thinking: bool = True
    show_graph_visualiser: bool = True
    show_cost_meter: bool = True
    auto_scroll_feed: bool = True
    sound_on_vote: bool = False
    sound_on_deadlock: bool = False
    demo_mode: bool = False


# ---------------------------------------------------------------------------
# Root config
# ---------------------------------------------------------------------------

class CouncilConfig(BaseModel):
    council: CouncilSettings = Field(default_factory=CouncilSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    agents: AgentsSettings = Field(default_factory=AgentsSettings)
    ingest: IngestConfig = Field(default_factory=IngestConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    ui: UIConfig = Field(default_factory=UIConfig)

    model_config = {"extra": "ignore"}
