"""RFC (Request for Comments) models for CodeCouncil."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RFCSection(BaseModel):
    """A single section within an RFC document."""

    title: str
    content: str
    order: int


class RFC(BaseModel):
    """The final RFC document produced by the Scribe agent."""

    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    version: int = 1
    repo_name: str
    created_at: datetime
    consensus_score: float = 0.0
    sections: list[RFCSection] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    total_cost_usd: float = 0.0
