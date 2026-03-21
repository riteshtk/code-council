"""LangGraph state definition for CodeCouncil."""

from typing import TypedDict


class CouncilState(TypedDict):
    """
    LangGraph state for a CodeCouncil run.

    Uses plain serializable types (str, dict, list, float, bool) for
    LangGraph compatibility. Pydantic models are validated and then
    converted to dicts before being stored in state.
    """

    run_id: str  # UUID as string for LangGraph serialization
    repo_url: str
    config: dict  # serialized CouncilConfig
    phase: str  # Phase value
    repo_context: dict | None
    findings: list[dict]
    proposals: list[dict]
    votes: list[dict]
    debate_rounds: list[dict]
    opening_statements: list[dict]
    rfc_content: str
    agent_memories: dict[str, dict]
    events: list[dict]
    cost_total: float
    human_review_pending: bool
    cancelled: bool
