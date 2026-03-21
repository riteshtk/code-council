"""Renderer registry — registers and looks up RFC renderers by format key."""

from __future__ import annotations

from .base import RFCRenderer


class RendererRegistry:
    _registry: dict[str, type[RFCRenderer]] = {}

    @classmethod
    def register(cls, renderer_cls: type[RFCRenderer]) -> type[RFCRenderer]:
        """Register a renderer class. Can be used as a decorator."""
        instance = renderer_cls()
        cls._registry[instance.format_key()] = renderer_cls
        return renderer_cls

    @classmethod
    def get(cls, key: str) -> RFCRenderer:
        """Return an instance of the renderer for the given format key."""
        if key not in cls._registry:
            raise KeyError(f"No renderer registered for format '{key}'. Available: {list(cls._registry)}")
        return cls._registry[key]()

    @classmethod
    def list_all(cls) -> list[str]:
        """Return all registered format keys."""
        return list(cls._registry.keys())


# ── Auto-register built-in renderers ─────────────────────────────────────────
# Import here (after RendererRegistry is defined) to avoid circular imports.
from .markdown import MarkdownRenderer  # noqa: E402
from .json_renderer import JSONRenderer  # noqa: E402
from .html import HTMLRenderer  # noqa: E402

RendererRegistry.register(MarkdownRenderer)
RendererRegistry.register(JSONRenderer)
RendererRegistry.register(HTMLRenderer)
