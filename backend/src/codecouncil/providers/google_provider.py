"""Google Generative AI (Gemini) provider implementation."""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

from codecouncil.providers.base import LLMConfig, LLMResponse, Message, ProviderPlugin

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai

    _GOOGLE_AVAILABLE = True
except ImportError:
    _GOOGLE_AVAILABLE = False


class GoogleProvider(ProviderPlugin):
    name = "google"

    def __init__(self, api_key: str | None = None) -> None:
        if not _GOOGLE_AVAILABLE:
            raise ImportError(
                "google-generativeai package is required for GoogleProvider. "
                "Install it with: pip install google-generativeai"
            )
        if api_key:
            genai.configure(api_key=api_key)
        self._api_key = api_key

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_model(self, model_name: str):
        return genai.GenerativeModel(model_name)

    def _build_contents(self, messages: list[Message]) -> tuple[str | None, list[dict]]:
        """Convert messages to Gemini format. Returns (system_instruction, contents)."""
        system: str | None = None
        contents: list[dict] = []

        for msg in messages:
            if msg.role == "system":
                system = msg.content
                continue
            # Gemini uses "user" and "model" roles
            role = "model" if msg.role == "assistant" else "user"
            contents.append({"role": role, "parts": [msg.content]})

        return system, contents

    async def _retry(self, fn, config: LLMConfig):
        for attempt in range(config.retry_attempts):
            try:
                return await asyncio.wait_for(fn(), timeout=config.timeout_seconds)
            except Exception as exc:
                if attempt == config.retry_attempts - 1:
                    raise
                wait = (2 ** attempt) * 0.5
                logger.warning(
                    "Google attempt %d/%d failed (%s). Retrying in %.1fs...",
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
        system, contents = self._build_contents(messages)
        model_kwargs: dict = {}
        if system:
            model_kwargs["system_instruction"] = system

        model = genai.GenerativeModel(config.model, **model_kwargs)

        generation_config = genai.types.GenerationConfig(
            temperature=config.temperature,
            max_output_tokens=config.max_tokens,
        )

        async def _call():
            return await model.generate_content_async(
                contents,
                generation_config=generation_config,
                stream=True,
            )

        response = await self._retry(_call, config)
        async for chunk in response:
            if chunk.text:
                yield chunk.text

    async def complete(self, messages: list[Message], config: LLMConfig) -> LLMResponse:
        system, contents = self._build_contents(messages)
        model_kwargs: dict = {}
        if system:
            model_kwargs["system_instruction"] = system

        model = genai.GenerativeModel(config.model, **model_kwargs)

        generation_config = genai.types.GenerationConfig(
            temperature=config.temperature,
            max_output_tokens=config.max_tokens,
        )

        async def _call():
            return await model.generate_content_async(
                contents,
                generation_config=generation_config,
                stream=False,
            )

        response = await self._retry(_call, config)
        text = response.text or ""
        usage = response.usage_metadata
        return LLMResponse(
            content=text,
            input_tokens=usage.prompt_token_count if usage else 0,
            output_tokens=usage.candidates_token_count if usage else 0,
            model=config.model,
            cached=False,
        )

    def count_tokens(self, text: str) -> int:
        # Approximate: ~4 chars per token
        return max(1, len(text) // 4)

    def supports_streaming(self) -> bool:
        return True

    def max_context_tokens(self) -> int:
        return 1_000_000  # Gemini 1.5 Pro supports 1M context
