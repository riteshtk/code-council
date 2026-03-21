"""Abstract base class and core data structures for debate topologies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from codecouncil.models.state import CouncilState


@dataclass
class AgentTurn:
    agent_handle: str
    action: str  # "present", "challenge", "respond", "propose", "vote", "summarize", "question"
    target_agent: str | None = None
    target_proposal: str | None = None


class DebateTopology(ABC):
    name: str

    @abstractmethod
    def get_turn_order(self, state: CouncilState, agents: list[str]) -> list[AgentTurn]:
        """Get the full turn order for a round."""
        ...

    @abstractmethod
    def can_interrupt(self, agent: str, current_speaker: str) -> bool:
        """Can this agent interrupt the current speaker?"""
        ...

    @abstractmethod
    def should_end_round(self, state: CouncilState, round_num: int, max_rounds: int) -> bool:
        """Should the current round end?"""
        ...

    @abstractmethod
    def get_next_speaker(
        self, state: CouncilState, last_turn: AgentTurn, agents: list[str]
    ) -> AgentTurn | None:
        """Get next speaker given the last turn. Returns None if round is done."""
        ...

    def on_deadlock(self, proposal_id: str, agent: str, evidence: str) -> None:
        """Handle deadlock declaration. Default: no-op."""
        pass
