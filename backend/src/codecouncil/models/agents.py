"""Agent models for CodeCouncil."""

from enum import StrEnum

from pydantic import BaseModel, Field


class DebateRole(StrEnum):
    """The role an agent plays in the debate."""

    ANALYST = "ANALYST"
    CHALLENGER = "CHALLENGER"
    PROPOSER = "PROPOSER"
    SCRIBE = "SCRIBE"
    MODERATOR = "MODERATOR"


class AgentStatus(StrEnum):
    """The current status of an agent."""

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    OBSERVING = "OBSERVING"


class AgentIdentity(BaseModel):
    """Static identity and configuration for an agent."""

    name: str
    handle: str
    color: str
    description: str = ""
    debate_role: DebateRole
    vote_weight: float = 1.0


class AgentMemory(BaseModel):
    """Persistent memory for an agent across sessions."""

    agent_handle: str
    session_summaries: list[str] = Field(default_factory=list)
    known_patterns: list[str] = Field(default_factory=list)
    interpersonal_history: list[str] = Field(default_factory=list)
    total_token_count: int = 0
