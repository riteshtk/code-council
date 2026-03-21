"""Socratic debate topology.

The engine acts as moderator.  Agents speak only when questioned.
Turn order: engine generates a question for each agent in sequence.
No interruptions.  Round ends when all agents have been questioned on
all proposals.
"""

from __future__ import annotations

from codecouncil.models.state import CouncilState

from .base import AgentTurn, DebateTopology


class SocraticTopology(DebateTopology):
    name = "socratic"

    def get_turn_order(self, state: CouncilState, agents: list[str]) -> list[AgentTurn]:
        """One 'question' turn per agent per proposal.

        For each proposal (or once if there are none) every agent gets a
        turn with action="question" so the engine can ask them something.
        """
        proposals = state.get("proposals", [])
        turns: list[AgentTurn] = []

        if not proposals:
            for agent in agents:
                turns.append(AgentTurn(agent_handle=agent, action="question"))
        else:
            for proposal in proposals:
                pid = proposal.get("id") if isinstance(proposal, dict) else None
                for agent in agents:
                    turns.append(
                        AgentTurn(
                            agent_handle=agent,
                            action="question",
                            target_proposal=pid,
                        )
                    )
        return turns

    def can_interrupt(self, agent: str, current_speaker: str) -> bool:
        """No interruptions — agents speak only when questioned."""
        return False

    def should_end_round(self, state: CouncilState, round_num: int, max_rounds: int) -> bool:
        """End when max rounds reached (all questioning done structurally by turn order)."""
        return round_num >= max_rounds

    def get_next_speaker(
        self, state: CouncilState, last_turn: AgentTurn, agents: list[str]
    ) -> AgentTurn | None:
        order = self.get_turn_order(state, agents)
        for i, turn in enumerate(order):
            if (
                turn.agent_handle == last_turn.agent_handle
                and turn.action == last_turn.action
                and turn.target_proposal == last_turn.target_proposal
            ):
                if i + 1 < len(order):
                    return order[i + 1]
                return None
        return None
