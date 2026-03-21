"""Event models for CodeCouncil."""

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(StrEnum):
    """All event types emitted during a CodeCouncil run."""

    RUN_STARTED = "RUN_STARTED"
    RUN_COMPLETED = "RUN_COMPLETED"
    RUN_FAILED = "RUN_FAILED"
    RUN_CANCELLED = "RUN_CANCELLED"
    PHASE_STARTED = "PHASE_STARTED"
    PHASE_COMPLETED = "PHASE_COMPLETED"
    INGEST_STARTED = "INGEST_STARTED"
    INGEST_COMPLETED = "INGEST_COMPLETED"
    AGENT_ACTIVATED = "AGENT_ACTIVATED"
    AGENT_THINKING = "AGENT_THINKING"
    AGENT_SPEAKING = "AGENT_SPEAKING"
    AGENT_DONE = "AGENT_DONE"
    AGENT_ADDRESSING = "AGENT_ADDRESSING"
    AGENT_PAUSED = "AGENT_PAUSED"
    FINDING_EMITTED = "FINDING_EMITTED"
    PROPOSAL_CREATED = "PROPOSAL_CREATED"
    PROPOSAL_CHALLENGED = "PROPOSAL_CHALLENGED"
    PROPOSAL_REVISED = "PROPOSAL_REVISED"
    PROPOSAL_WITHDRAWN = "PROPOSAL_WITHDRAWN"
    PROPOSAL_DEADLOCKED = "PROPOSAL_DEADLOCKED"
    VOTE_CAST = "VOTE_CAST"
    ROUND_STARTED = "ROUND_STARTED"
    ROUND_ENDED = "ROUND_ENDED"
    DEADLOCK_DECLARED = "DEADLOCK_DECLARED"
    CONSENSUS_REACHED = "CONSENSUS_REACHED"
    HUMAN_CHALLENGE = "HUMAN_CHALLENGE"
    HUMAN_OVERRIDE = "HUMAN_OVERRIDE"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    HITL_TIMEOUT = "HITL_TIMEOUT"
    RFC_STARTED = "RFC_STARTED"
    RFC_SECTION_COMPLETED = "RFC_SECTION_COMPLETED"
    RFC_FINALISED = "RFC_FINALISED"
    BUDGET_WARNING = "BUDGET_WARNING"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"


class Phase(StrEnum):
    """Phases of a CodeCouncil run."""

    INGESTING = "INGESTING"
    ANALYSING = "ANALYSING"
    OPENING = "OPENING"
    DEBATING = "DEBATING"
    VOTING = "VOTING"
    SCRIBING = "SCRIBING"
    REVIEW = "REVIEW"
    DONE = "DONE"


class EventMetadata(BaseModel):
    """Metadata attached to an event for cost/performance tracking."""

    provider: str | None = None
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    cached: bool = False
    fallback: bool = False


class Event(BaseModel):
    """A single event emitted during a CodeCouncil run."""

    event_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    session_id: UUID | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sequence: int = 0
    agent: str
    event_type: EventType
    phase: Phase
    round: int | None = None
    content: str
    structured: dict = Field(default_factory=dict)
    metadata: EventMetadata = Field(default_factory=EventMetadata)
