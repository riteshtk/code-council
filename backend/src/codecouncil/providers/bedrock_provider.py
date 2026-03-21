"""AWS Bedrock provider implementation."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from codecouncil.providers.base import LLMConfig, LLMResponse, Message, ProviderPlugin

logger = logging.getLogger(__name__)

try:
    import boto3

    _BOTO3_AVAILABLE = True
except ImportError:
    _BOTO3_AVAILABLE = False

try:
    import tiktoken

    _TIKTOKEN_AVAILABLE = True
except ImportError:
    _TIKTOKEN_AVAILABLE = False


class BedrockProvider(ProviderPlugin):
    name = "bedrock"

    def __init__(
        self,
        region_name: str = "us-east-1",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        profile_name: str | None = None,
    ) -> None:
        if not _BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 package is required for BedrockProvider. "
                "Install it with: pip install boto3"
            )
        session_kwargs: dict = {}
        if profile_name:
            session_kwargs["profile_name"] = profile_name
        if aws_access_key_id:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key:
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key

        session = boto3.Session(**session_kwargs)
        self._client = session.client("bedrock-runtime", region_name=region_name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_body(self, messages: list[Message], config: LLMConfig) -> dict:
        """Build the request body for Anthropic Claude models on Bedrock."""
        system: str | None = None
        turns: list[dict] = []
        for msg in messages:
            if msg.role == "system":
                system = msg.content
                continue
            turns.append({"role": msg.role, "content": msg.content})

        body: dict = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "messages": turns,
        }
        if system:
            body["system"] = system
        return body

    async def _retry(self, fn, config: LLMConfig):
        for attempt in range(config.retry_attempts):
            try:
                return await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, fn),
                    timeout=config.timeout_seconds,
                )
            except Exception as exc:
                if attempt == config.retry_attempts - 1:
                    raise
                wait = (2 ** attempt) * 0.5
                logger.warning(
                    "Bedrock attempt %d/%d failed (%s). Retrying in %.1fs...",
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
        body = self._build_body(messages, config)
        body_bytes = json.dumps(body).encode()

        def _invoke():
            return self._client.invoke_model_with_response_stream(
                modelId=config.model,
                body=body_bytes,
                contentType="application/json",
                accept="application/json",
            )

        response = await self._retry(_invoke, config)
        event_stream = response.get("body")
        if event_stream is None:
            return

        for event in event_stream:
            chunk = event.get("chunk")
            if chunk:
                data = json.loads(chunk["bytes"].decode())
                if data.get("type") == "content_block_delta":
                    delta = data.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        if text:
                            yield text

    async def complete(self, messages: list[Message], config: LLMConfig) -> LLMResponse:
        body = self._build_body(messages, config)
        body_bytes = json.dumps(body).encode()

        def _invoke():
            return self._client.invoke_model(
                modelId=config.model,
                body=body_bytes,
                contentType="application/json",
                accept="application/json",
            )

        response = await self._retry(_invoke, config)
        response_body = json.loads(response["body"].read())

        content = "".join(
            block.get("text", "")
            for block in response_body.get("content", [])
            if block.get("type") == "text"
        )
        usage = response_body.get("usage", {})
        return LLMResponse(
            content=content,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            model=config.model,
            cached=False,
        )

    def count_tokens(self, text: str) -> int:
        if _TIKTOKEN_AVAILABLE:
            try:
                enc = tiktoken.get_encoding("cl100k_base")
                return len(enc.encode(text))
            except Exception:
                pass
        return max(1, len(text) // 4)

    def supports_streaming(self) -> bool:
        return True

    def max_context_tokens(self) -> int:
        return 200_000
