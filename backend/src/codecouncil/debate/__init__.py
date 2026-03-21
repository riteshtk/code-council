"""Debate topology package for CodeCouncil."""

from .adversarial import AdversarialTopology
from .base import AgentTurn, DebateTopology
from .collaborative import CollaborativeTopology
from .custom import CustomTopology
from .open_floor import OpenFloorTopology
from .panel import PanelTopology
from .registry import TopologyRegistry
from .socratic import SocraticTopology

__all__ = [
    "AgentTurn",
    "DebateTopology",
    "TopologyRegistry",
    "AdversarialTopology",
    "CollaborativeTopology",
    "SocraticTopology",
    "OpenFloorTopology",
    "PanelTopology",
    "CustomTopology",
]
