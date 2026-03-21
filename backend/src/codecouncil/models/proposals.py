"""Proposal models for CodeCouncil."""

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ProposalStatus(StrEnum):
    """Lifecycle status of a proposal."""

    PROPOSED = "PROPOSED"
    CHALLENGED = "CHALLENGED"
    REVISED = "REVISED"
    VOTED = "VOTED"
    PASSED = "PASSED"
    FAILED = "FAILED"
    DEADLOCKED = "DEADLOCKED"
    WITHDRAWN = "WITHDRAWN"


class Proposal(BaseModel):
    """A proposal made by an agent during the debate phase."""

    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    proposal_number: int
    version: int = 1
    title: str
    goal: str = ""
    effort: str = "M"
    status: ProposalStatus = ProposalStatus.PROPOSED
    author_agent: str
    breaking_change: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
