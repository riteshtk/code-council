"""Topology registry — maps topology names to their classes."""

from __future__ import annotations

from .base import DebateTopology


class TopologyRegistry:
    _topologies: dict[str, type[DebateTopology]] = {}

    @classmethod
    def register(cls, name: str, topology_class: type[DebateTopology]) -> None:
        """Register a topology class under the given name."""
        cls._topologies[name] = topology_class

    @classmethod
    def get(cls, name: str) -> DebateTopology:
        """Instantiate and return a topology by name.

        Raises KeyError if the topology is not registered.
        """
        try:
            return cls._topologies[name]()
        except KeyError:
            available = ", ".join(sorted(cls._topologies))
            raise KeyError(
                f"Unknown topology {name!r}. Available: {available}"
            ) from None

    @classmethod
    def list_all(cls) -> list[str]:
        """Return a sorted list of all registered topology names."""
        return sorted(cls._topologies)


def _auto_register() -> None:
    """Import all built-in topologies and register them."""
    # Local imports to avoid circular dependencies at module level
    from .adversarial import AdversarialTopology
    from .collaborative import CollaborativeTopology
    from .custom import CustomTopology
    from .open_floor import OpenFloorTopology
    from .panel import PanelTopology
    from .socratic import SocraticTopology

    for cls in (
        AdversarialTopology,
        CollaborativeTopology,
        SocraticTopology,
        OpenFloorTopology,
        PanelTopology,
        CustomTopology,
    ):
        TopologyRegistry.register(cls.name, cls)


_auto_register()
