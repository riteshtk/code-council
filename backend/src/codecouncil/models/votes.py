"""Vote models for CodeCouncil."""

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class VoteType(StrEnum):
    """The type of vote cast by an agent."""

    YES = "YES"
    NO = "NO"
    ABSTAIN = "ABSTAIN"


class Vote(BaseModel):
    """A vote cast by an agent on a proposal."""

    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    proposal_id: UUID
    agent: str
    vote: VoteType
    rationale: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
