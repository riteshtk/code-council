"""Mistral AI provider implementation."""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

from codecouncil.providers.base import LLMConfig, LLMResponse, Message, ProviderPlugin

logger = logging.getLogger(__name__)

try:
    from mistralai import Mistral
    import tiktoken

    _MISTRAL_AVAILABLE = True
except ImportError:
    _MISTRAL_AVAILABLE = False


class MistralProvider(ProviderPlugin):
    name = "mistral"

    def __init__(self, api_key: str | None = None) -> None:
        if not _MISTRAL_AVAILABLE:
            raise ImportError(
                "mistralai and tiktoken packages are required for MistralProvider. "
                "Install them with: pip install mistralai tiktoken"
            )
        self._client = Mistral(api_key=api_key or "")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_messages(self, messages: list[Message]) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in messages]

    async def _retry(self, fn, config: LLMConfig):
        for attempt in range(config.retry_attempts):
            try:
                return await asyncio.wait_for(fn(), timeout=config.timeout_seconds)
            except Exception as exc:
                if attempt == config.retry_attempts - 1:
                    raise
                wait = (2 ** attempt) * 0.5
                logger.warning(
                    "Mistral attempt %d/%d failed (%s). Retrying in %.1fs...",
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
        msgs = self._build_messages(messages)

        async def _call():
            return self._client.chat.stream_async(
                model=config.model,
                messages=msgs,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )

        stream_ctx = await self._retry(_call, config)
        async with stream_ctx as stream:
            async for chunk in stream:
                delta = chunk.data.choices[0].delta.content if chunk.data.choices else None
                if delta:
                    yield delta

    async def complete(self, messages: list[Message], config: LLMConfig) -> LLMResponse:
        msgs = self._build_messages(messages)

        async def _call():
            return await self._client.chat.complete_async(
                model=config.model,
                messages=msgs,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )

        response = await self._retry(_call, config)
        choice = response.choices[0]
        usage = response.usage
        return LLMResponse(
            content=choice.message.content or "",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            model=response.model or config.model,
            cached=False,
        )

    def count_tokens(self, text: str) -> int:
        # Use tiktoken cl100k as a reasonable estimate for Mistral
        try:
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            return max(1, len(text) // 4)

    def supports_streaming(self) -> bool:
        return True

    def max_context_tokens(self) -> int:
        return 32_768
