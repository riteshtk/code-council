"""Provider info and test endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["providers"])

# Known provider names with their metadata
_PROVIDERS = [
    {"name": "openai",    "display_name": "OpenAI",          "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]},
    {"name": "anthropic", "display_name": "Anthropic",        "models": ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-3-5"]},
    {"name": "google",    "display_name": "Google Gemini",    "models": ["gemini-2.0-flash", "gemini-1.5-pro"]},
    {"name": "mistral",   "display_name": "Mistral AI",       "models": ["mistral-large-latest", "mistral-medium"]},
    {"name": "ollama",    "display_name": "Ollama (local)",   "models": ["llama3", "mistral", "codellama"]},
    {"name": "bedrock",   "display_name": "AWS Bedrock",      "models": ["anthropic.claude-3-5-sonnet-20241022-v2:0"]},
    {"name": "azure",     "display_name": "Azure OpenAI",     "models": ["gpt-4o", "gpt-4-turbo"]},
]


@router.get("/providers")
async def list_providers() -> dict:
    """Return all known LLM providers and their available models."""
    return {"providers": _PROVIDERS}


class TestProviderRequest(BaseModel):
    provider: str
    model: str | None = None


@router.post("/providers/test")
async def test_provider(body: TestProviderRequest) -> dict:
    """Test connectivity to a provider (lightweight probe)."""
    known_names = {p["name"] for p in _PROVIDERS}
    if body.provider not in known_names:
        return {
            "provider": body.provider,
            "success": False,
            "error": f"Unknown provider '{body.provider}'",
        }
    # We don't actually call the provider in tests / without credentials;
    # return a canned "not configured" response.
    return {
        "provider": body.provider,
        "success": False,
        "error": "Provider not configured (no API key set)",
    }
