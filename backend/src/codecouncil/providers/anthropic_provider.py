"""Anthropic provider implementation with prompt caching support."""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

from codecouncil.providers.base import LLMConfig, LLMResponse, Message, ProviderPlugin

logger = logging.getLogger(__name__)

try:
    import anthropic

    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


class AnthropicProvider(ProviderPlugin):
    name = "anthropic"

    def __init__(self, api_key: str | None = None) -> None:
        if not _ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package is required for AnthropicProvider. "
                "Install it with: pip install anthropic"
            )
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_messages(
        self, messages: list[Message]
    ) -> tuple[str | None, list[dict]]:
        """Split messages into system prompt + user/assistant turns.

        Returns (system_text, turns) where turns is the list for the API.
        Adds cache_control to message content when present on the Message object.
        """
        system: str | None = None
        turns: list[dict] = []

        for msg in messages:
            if msg.role == "system":
                system = msg.content
                continue

            content: list[dict] | str
            if msg.cache_control is not None:
                content = [
                    {
                        "type": "text",
                        "text": msg.content,
                        "cache_control": msg.cache_control,
                    }
                ]
            else:
                content = msg.content

            turns.append({"role": msg.role, "content": content})

        return system, turns

    async def _retry(self, fn, config: LLMConfig):
        for attempt in range(config.retry_attempts):
            try:
                return await asyncio.wait_for(fn(), timeout=config.timeout_seconds)
            except Exception as exc:
                if attempt == config.retry_attempts - 1:
                    raise
                wait = (2 ** attempt) * 0.5
                logger.warning(
                    "Anthropic attempt %d/%d failed (%s). Retrying in %.1fs...",
                    attempt + 1,
                    config.retry_attempts,
                    exc,
                    wait,
                )
                await asyncio.sleep(wait)

    # ------------------------------------------------------------------
    # ProviderPlugin interface
    # ------------------------------------------------------------------

    async def stream(self, messages: list[Message], config: LLMConfig) -> AsyncIterator[str]:
        system, turns = self._build_messages(messages)

        kwargs: dict = dict(
            model=config.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            messages=turns,
        )
        if system:
            kwargs["system"] = system

        async def _call():
            return self._client.messages.stream(**kwargs)

        stream_ctx = await self._retry(_call, config)
        async with stream_ctx as stream:
            async for text in stream.text_stream:
                yield text

    async def complete(self, messages: list[Message], config: LLMConfig) -> LLMResponse:
        system, turns = self._build_messages(messages)

        kwargs: dict = dict(
            model=config.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            messages=turns,
        )
        if system:
            kwargs["system"] = system

        async def _call():
            return await self._client.messages.create(**kwargs)

        response = await self._retry(_call, config)
        content = "".join(
            block.text for block in response.content if hasattr(block, "text")
        )
        usage = response.usage
        cached = False
        if hasattr(usage, "cache_read_input_tokens") and usage.cache_read_input_tokens:
            cached = True

        return LLMResponse(
            content=content,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            model=response.model,
            cached=cached,
        )

    def count_tokens(self, text: str) -> int:
        # Approximate: Anthropic uses ~4 chars per token on average
        return max(1, len(text) // 4)

    def supports_streaming(self) -> bool:
        return True

    def max_context_tokens(self) -> int:
        return 200_000
