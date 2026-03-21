"""CodeCouncil LLM provider system.

Re-exports the public API surface for the providers package.
"""
from codecouncil.providers.base import LLMConfig, LLMResponse, Message, ProviderPlugin
from codecouncil.providers.cost import CostTracker, LLMCallRecord
from codecouncil.providers.registry import ProviderRegistry

# Lazy imports for concrete providers so missing SDKs don't break the package
from codecouncil.providers.openai_provider import OpenAIProvider
from codecouncil.providers.anthropic_provider import AnthropicProvider
from codecouncil.providers.google_provider import GoogleProvider
from codecouncil.providers.mistral_provider import MistralProvider
from codecouncil.providers.ollama_provider import OllamaProvider
from codecouncil.providers.bedrock_provider import BedrockProvider
from codecouncil.providers.azure_provider import AzureOpenAIProvider

__all__ = [
    # Base types
    "Message",
    "LLMConfig",
    "LLMResponse",
    "ProviderPlugin",
    # Registry
    "ProviderRegistry",
    # Cost tracking
    "CostTracker",
    "LLMCallRecord",
    # Concrete providers
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "MistralProvider",
    "OllamaProvider",
    "BedrockProvider",
    "AzureOpenAIProvider",
]
