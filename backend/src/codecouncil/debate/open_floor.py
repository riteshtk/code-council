"""Open-floor debate topology.

Any agent can respond to any other.  Max 1 response per agent per turn.
All agents can interrupt.  Round ends when all agents have spoken or
max responses reached.
"""

from __future__ import annotations

from codecouncil.models.state import CouncilState

from .base import AgentTurn, DebateTopology


class OpenFloorTopology(DebateTopology):
    name = "open_floor"

    def get_turn_order(self, state: CouncilState, agents: list[str]) -> list[AgentTurn]:
        """Each agent gets one 'present' turn in list order."""
        return [AgentTurn(agent_handle=agent, action="present") for agent in agents]

    def can_interrupt(self, agent: str, current_speaker: str) -> bool:
        """Any agent may interrupt any other."""
        return True

    def should_end_round(self, state: CouncilState, round_num: int, max_rounds: int) -> bool:
        """End when max rounds reached."""
        return round_num >= max_rounds

    def get_next_speaker(
        self, state: CouncilState, last_turn: AgentTurn, agents: list[str]
    ) -> AgentTurn | None:
        order = self.get_turn_order(state, agents)
        for i, turn in enumerate(order):
            if turn.agent_handle == last_turn.agent_handle:
                if i + 1 < len(order):
                    return order[i + 1]
                return None
        return None
