"""Custom debate topology.

Parses a YAML-style list of step dicts.  Each step has the shape:
    {agent: str, action: str, target?: str, condition?: str}

Simple condition expressions ("if skeptic.vote == no") are evaluated
against the CouncilState votes list.  Steps whose condition evaluates
to False are skipped.
"""

from __future__ import annotations

import re
from typing import Any

from codecouncil.models.state import CouncilState

from .base import AgentTurn, DebateTopology


def _eval_condition(condition: str, state: CouncilState) -> bool:
    """Evaluate a simple condition string against state.

    Supported syntax:  "if <agent>.vote == <value>"
    Returns True when the condition holds or cannot be parsed
    (fail-open so unknown conditions don't silently drop steps).
    """
    if not condition:
        return True

    # Strip leading "if "
    expr = re.sub(r"^\s*if\s+", "", condition).strip()

    # Match: <agent>.vote == <value>
    m = re.match(r"^(\w+)\.vote\s*==\s*(\w+)$", expr)
    if m:
        agent_name, expected_value = m.group(1), m.group(2)
        votes: list[dict] = state.get("votes", [])  # type: ignore[assignment]
        for vote in votes:
            if vote.get("agent_handle") == agent_name:
                return str(vote.get("vote", "")).lower() == expected_value.lower()
        # Agent hasn't voted yet → condition not satisfied
        return False

    # Unknown condition: fail-open
    return True


class CustomTopology(DebateTopology):
    name = "custom"

    def __init__(self, steps: list[dict[str, Any]] | None = None) -> None:
        self._steps: list[dict[str, Any]] = steps or []

    def get_turn_order(self, state: CouncilState, agents: list[str]) -> list[AgentTurn]:
        """Convert step dicts to AgentTurn objects, applying conditions."""
        turns: list[AgentTurn] = []
        for step in self._steps:
            condition = step.get("condition", "")
            if condition and not _eval_condition(condition, state):
                continue
            turns.append(
                AgentTurn(
                    agent_handle=step["agent"],
                    action=step["action"],
                    target_agent=step.get("target"),
                    target_proposal=step.get("target_proposal"),
                )
            )
        return turns

    def can_interrupt(self, agent: str, current_speaker: str) -> bool:
        """Custom topologies do not allow interruptions by default."""
        return False

    def should_end_round(self, state: CouncilState, round_num: int, max_rounds: int) -> bool:
        return round_num >= max_rounds

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
