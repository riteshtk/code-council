"""Panel debate topology.

Fixed rotation: Archaeologist → Skeptic → Visionary → others.
One proposal per round.  No interruptions.
Vote immediately after each proposal's round.
"""

from __future__ import annotations

from codecouncil.models.state import CouncilState

from .base import AgentTurn, DebateTopology

# Canonical panel order for named roles
_PANEL_ORDER = ["archaeologist", "skeptic", "visionary"]


class PanelTopology(DebateTopology):
    name = "panel"

    def get_turn_order(self, state: CouncilState, agents: list[str]) -> list[AgentTurn]:
        """Produce turns in panel rotation order.

        Named roles come first in the fixed order; any remaining agents
        follow in the order they appear in the ``agents`` list.
        """
        turns: list[AgentTurn] = []
        emitted: set[str] = set()

        for role in _PANEL_ORDER:
            if role in agents:
                turns.append(AgentTurn(agent_handle=role, action="present"))
                emitted.add(role)

        for agent in agents:
            if agent not in emitted:
                turns.append(AgentTurn(agent_handle=agent, action="present"))

        return turns

    def can_interrupt(self, agent: str, current_speaker: str) -> bool:
        """No interruptions in panel format."""
        return False

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
