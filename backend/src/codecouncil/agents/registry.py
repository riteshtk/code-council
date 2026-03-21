"""Agent registry for CodeCouncil."""

from codecouncil.agents.base import BaseAgent
from codecouncil.models.agents import DebateRole


class AgentRegistry:
    """Registry for managing agent instances."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, handle: str, agent: BaseAgent) -> None:
        """Register an agent by handle."""
        self._agents[handle] = agent

    def get(self, handle: str) -> BaseAgent:
        """Retrieve an agent by handle. Raises KeyError if not found."""
        if handle not in self._agents:
            raise KeyError(f"Agent '{handle}' not registered")
        return self._agents[handle]

    def list_all(self) -> dict[str, BaseAgent]:
        """Return all registered agents."""
        return dict(self._agents)

    def get_voting_agents(self) -> list[BaseAgent]:
        """Return agents that vote (exclude Scribe from proposal votes)."""
        return [
            agent
            for agent in self._agents.values()
            if agent.identity.debate_role != DebateRole.SCRIBE
        ]

    def get_analyst_agents(self) -> list[BaseAgent]:
        """Return agents that run analysis (exclude Scribe)."""
        return [
            agent
            for agent in self._agents.values()
            if agent.identity.debate_role != DebateRole.SCRIBE
        ]
