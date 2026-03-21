"""CodeCouncil agent system."""

from codecouncil.agents.archaeologist import Archaeologist
from codecouncil.agents.base import AgentResponse, BaseAgent, DebateContext
from codecouncil.agents.definition import AgentDefinition
from codecouncil.agents.memory import AgentMemoryManager
from codecouncil.agents.registry import AgentRegistry
from codecouncil.agents.scribe import Scribe
from codecouncil.agents.skeptic import Skeptic
from codecouncil.agents.visionary import Visionary

__all__ = [
    "AgentDefinition",
    "BaseAgent",
    "DebateContext",
    "AgentResponse",
    "AgentRegistry",
    "AgentMemoryManager",
    "Archaeologist",
    "Skeptic",
    "Visionary",
    "Scribe",
]
