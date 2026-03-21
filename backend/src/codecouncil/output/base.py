"""Abstract base class for RFC renderers."""

from abc import ABC, abstractmethod


class RFCRenderer(ABC):
    @abstractmethod
    def render(self, state: dict) -> str:
        """Render RFC from council state."""
        ...

    @abstractmethod
    def format_key(self) -> str:
        """Return format identifier (e.g., 'markdown', 'json', 'html')."""
        ...
