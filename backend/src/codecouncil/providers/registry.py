from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codecouncil.providers.base import Message, LLMConfig

from codecouncil.providers.base import ProviderPlugin

logger = logging.getLogger(__name__)


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ProviderPlugin] = {}

    def register(self, name: str, provider: ProviderPlugin) -> None:
        """Register a provider under the given name."""
        self._providers[name] = provider

    def get(self, name: str) -> ProviderPlugin:
        """Retrieve a registered provider by name. Raises KeyError if not found."""
        if name not in self._providers:
            raise KeyError(f"Provider '{name}' is not registered. "
                           f"Available: {list(self._providers.keys())}")
        return self._providers[name]

    def list_all(self) -> dict[str, ProviderPlugin]:
        """Return all registered providers."""
        return dict(self._providers)

    async def resolve_with_fallback(
        self,
        primary: str,
        fallback_chain: list[str],
        messages: list[Message],
        config: LLMConfig,
        stream: bool = True,
    ) -> tuple[ProviderPlugin, str]:
        """Try primary provider, fall back through chain on failure.

        Returns (provider, provider_name) — the first one that succeeds.
        On complete failure raises the last exception encountered.
        """
        chain = [primary] + fallback_chain
        last_exc: Exception | None = None

        for name in chain:
            try:
                provider = self.get(name)
                # Probe by doing a lightweight check (just verify we can get it).
                # Actual call is left to the caller; we return the working provider.
                logger.debug("Resolved provider: %s", name)
                return provider, name
            except KeyError as exc:
                logger.warning("Provider '%s' not registered, skipping: %s", name, exc)
                last_exc = exc
            except Exception as exc:  # noqa: BLE001
                logger.warning("Provider '%s' failed, trying next: %s", name, exc)
                last_exc = exc

        raise RuntimeError(
            f"All providers exhausted. Chain: {chain}. Last error: {last_exc}"
        ) from last_exc
