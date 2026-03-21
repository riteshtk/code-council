"""Adversarial debate topology (default).

Turn order per proposal:
  Visionary presents → Skeptic challenges → Visionary responds →
  Others weigh in → Skeptic final word

Only the Skeptic may declare deadlock (interrupt) at any time.
"""

from __future__ import annotations

from codecouncil.models.state import CouncilState

from .base import AgentTurn, DebateTopology


class AdversarialTopology(DebateTopology):
    name = "adversarial"

    def get_turn_order(self, state: CouncilState, agents: list[str]) -> list[AgentTurn]:
        """Build a turn sequence for one round.

        Fixed spine: visionary propose → skeptic challenge → visionary respond →
        every other agent weighs in → skeptic final word.
        """
        turns: list[AgentTurn] = []

        # 1. Visionary opens with a proposal
        turns.append(AgentTurn(agent_handle="visionary", action="propose"))

        # 2. Skeptic challenges
        turns.append(
            AgentTurn(agent_handle="skeptic", action="challenge", target_agent="visionary")
        )

        # 3. Visionary responds
        turns.append(
            AgentTurn(agent_handle="visionary", action="respond", target_agent="skeptic")
        )

        # 4. All other agents weigh in (neither visionary nor skeptic)
        others = [a for a in agents if a not in ("visionary", "skeptic")]
        for agent in others:
            turns.append(AgentTurn(agent_handle=agent, action="present"))

        # 5. Skeptic has the final word
        turns.append(AgentTurn(agent_handle="skeptic", action="summarize"))

        return turns

    def can_interrupt(self, agent: str, current_speaker: str) -> bool:
        """Only the Skeptic can interrupt (to declare deadlock)."""
        return agent == "skeptic"

    def should_end_round(self, state: CouncilState, round_num: int, max_rounds: int) -> bool:
        """End when max rounds reached or all proposals have been addressed."""
        if round_num >= max_rounds:
            return True
        # Check whether all proposals already have votes recorded
        proposals = state.get("proposals", [])
        votes = state.get("votes", [])
        if proposals:
            voted_ids = {v.get("proposal_id") for v in votes}
            all_addressed = all(
                p.get("id") in voted_ids for p in proposals if p.get("id")
            )
            if all_addressed:
                return True
        return False

    def get_next_speaker(
        self, state: CouncilState, last_turn: AgentTurn, agents: list[str]
    ) -> AgentTurn | None:
        """Advance through the fixed sequence; return None at end."""
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

    def on_deadlock(self, proposal_id: str, agent: str, evidence: str) -> None:
        """Skeptic can invoke deadlock on any proposal."""
        # Concrete handling (e.g. persisting) is done by the graph layer.
        pass
