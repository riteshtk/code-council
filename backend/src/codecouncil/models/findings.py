"""Finding models for CodeCouncil."""

from datetime import datetime, timezone
from enum import IntEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Severity(IntEnum):
    """Severity level for a finding."""

    INFO = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class Finding(BaseModel):
    """A finding emitted by an agent during analysis."""

    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    agent: str
    severity: Severity
    scope: str = ""
    content: str
    implication: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
