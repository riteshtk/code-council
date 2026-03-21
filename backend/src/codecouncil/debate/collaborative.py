"""Collaborative debate topology.

Turn order: Archaeologist → Visionary → Skeptic (must include mitigations).
No interruptions allowed.  No agent may vote NO without proposing an alternative.
Round ends when modified consensus is reached or max rounds hit.
"""

from __future__ import annotations

from codecouncil.models.state import CouncilState

from .base import AgentTurn, DebateTopology


class CollaborativeTopology(DebateTopology):
    name = "collaborative"

    def get_turn_order(self, state: CouncilState, agents: list[str]) -> list[AgentTurn]:
        """Fixed spine: archaeologist → visionary → skeptic, then remaining agents."""
        priority = ["archaeologist", "visionary", "skeptic"]
        turns: list[AgentTurn] = []

        # Priority agents in fixed order
        for agent in priority:
            if agent in agents:
                turns.append(AgentTurn(agent_handle=agent, action="present"))

        # Remaining agents follow in their given order
        for agent in agents:
            if agent not in priority:
                turns.append(AgentTurn(agent_handle=agent, action="present"))

        return turns

    def can_interrupt(self, agent: str, current_speaker: str) -> bool:
        """Strict turns — no interruptions."""
        return False

    def should_end_round(self, state: CouncilState, round_num: int, max_rounds: int) -> bool:
        """End when max rounds reached or all votes are YES (consensus)."""
        if round_num >= max_rounds:
            return True
        votes = state.get("votes", [])
        proposals = state.get("proposals", [])
        if proposals and votes:
            if all(v.get("vote") == "yes" for v in votes):
                return True
        return False

    def get_next_speaker(
        self, state: CouncilState, last_turn: AgentTurn, agents: list[str]
    ) -> AgentTurn | None:
        order = self.get_turn_order(state, agents)
        for i, turn in enumerate(order):
            if (
                turn.agent_handle == last_turn.agent_handle
                and turn.action == last_turn.action
            ):
                if i + 1 < len(order):
                    return order[i + 1]
                return None
        return None
