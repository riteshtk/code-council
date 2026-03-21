from abc import ABC, abstractmethod
from typing import AsyncIterator
from dataclasses import dataclass, field


@dataclass
class Message:
    role: str  # "system", "user", "assistant"
    content: str
    cache_control: dict | None = None  # For Anthropic prompt caching


@dataclass
class LLMConfig:
    model: str = "gpt-4o"
    temperature: float = 0.3
    max_tokens: int = 2000
    streaming: bool = True
    timeout_seconds: int = 120
    retry_attempts: int = 3
    retry_backoff: str = "exponential"


@dataclass
class LLMResponse:
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    cached: bool = False


class ProviderPlugin(ABC):
    name: str

    @abstractmethod
    async def stream(self, messages: list[Message], config: LLMConfig) -> AsyncIterator[str]:
        """Stream response tokens."""
        ...

    @abstractmethod
    async def complete(self, messages: list[Message], config: LLMConfig) -> LLMResponse:
        """Get complete response (non-streaming)."""
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens for the given text."""
        ...

    @abstractmethod
    def supports_streaming(self) -> bool: ...

    @abstractmethod
    def max_context_tokens(self) -> int: ...
