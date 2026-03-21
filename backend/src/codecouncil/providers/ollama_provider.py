"""Ollama provider — local models via the OpenAI-compatible API."""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

from codecouncil.providers.base import LLMConfig, LLMResponse, Message, ProviderPlugin

logger = logging.getLogger(__name__)

try:
    import openai
    import tiktoken

    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

# Context sizes for common Ollama models (in tokens)
_MODEL_CONTEXT: dict[str, int] = {
    "llama3": 8_192,
    "llama3.1": 131_072,
    "llama3.2": 131_072,
    "mistral": 32_768,
    "mixtral": 32_768,
    "codellama": 16_384,
    "phi3": 128_000,
    "gemma": 8_192,
    "gemma2": 8_192,
    "qwen2": 131_072,
}

_DEFAULT_CONTEXT = 8_192


class OllamaProvider(ProviderPlugin):
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434/v1") -> None:
        if not _OPENAI_AVAILABLE:
            raise ImportError(
                "openai and tiktoken packages are required for OllamaProvider. "
                "Install them with: pip install openai tiktoken"
            )
        self._client = openai.AsyncOpenAI(
            base_url=base_url,
            api_key="ollama",  # Ollama doesn't require a real key
        )
        self._base_url = base_url

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
                    "Ollama attempt %d/%d failed (%s). Retrying in %.1fs...",
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
            return await self._client.chat.completions.create(
                model=config.model,
                messages=msgs,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                stream=True,
            )

        stream_obj = await self._retry(_call, config)
        async for chunk in stream_obj:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

    async def complete(self, messages: list[Message], config: LLMConfig) -> LLMResponse:
        msgs = self._build_messages(messages)

        async def _call():
            return await self._client.chat.completions.create(
                model=config.model,
                messages=msgs,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                stream=False,
            )

        response = await self._retry(_call, config)
        choice = response.choices[0]
        usage = response.usage or None
        return LLMResponse(
            content=choice.message.content or "",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            model=response.model,
            cached=False,
        )

    def count_tokens(self, text: str) -> int:
        try:
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            return max(1, len(text) // 4)

    def supports_streaming(self) -> bool:
        return True

    def max_context_tokens(self) -> int:
        # Can't know the model at init time; return a common default
        return _DEFAULT_CONTEXT
