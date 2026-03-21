from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LLMCallRecord:
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    cached: bool
    fallback: bool
    agent: str


class CostTracker:
    # Pricing table: provider -> model -> {input_per_1m, output_per_1m}
    PRICING: dict[str, dict[str, dict[str, float]]] = {
        "openai": {
            "gpt-4o": {"input_per_1m": 2.50, "output_per_1m": 10.00},
            "gpt-4o-mini": {"input_per_1m": 0.15, "output_per_1m": 0.60},
            "gpt-4-turbo": {"input_per_1m": 10.00, "output_per_1m": 30.00},
        },
        "anthropic": {
            "claude-sonnet-4-20250514": {"input_per_1m": 3.00, "output_per_1m": 15.00},
            "claude-haiku-4-5-20251001": {"input_per_1m": 0.80, "output_per_1m": 4.00},
            "claude-opus-4-20250514": {"input_per_1m": 15.00, "output_per_1m": 75.00},
        },
        "google": {
            "gemini-2.0-flash": {"input_per_1m": 0.10, "output_per_1m": 0.40},
            "gemini-2.5-pro": {"input_per_1m": 1.25, "output_per_1m": 10.00},
        },
        "mistral": {
            "mistral-large-latest": {"input_per_1m": 2.00, "output_per_1m": 6.00},
            "mistral-small-latest": {"input_per_1m": 0.20, "output_per_1m": 0.60},
        },
        "ollama": {},  # Free (local)
        "bedrock": {  # Same as base provider pricing roughly
            "anthropic.claude-3-sonnet": {"input_per_1m": 3.00, "output_per_1m": 15.00},
        },
        "azure": {},  # Same as OpenAI pricing
    }

    def __init__(self) -> None:
        self._records: list[LLMCallRecord] = []

    def calculate_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate the USD cost for the given token counts. Returns 0.0 for unknown models."""
        provider_pricing = self.PRICING.get(provider, {})
        model_pricing = provider_pricing.get(model)
        if model_pricing is None:
            return 0.0
        input_cost = (input_tokens / 1_000_000) * model_pricing["input_per_1m"]
        output_cost = (output_tokens / 1_000_000) * model_pricing["output_per_1m"]
        return input_cost + output_cost

    def record_call(self, record: LLMCallRecord) -> None:
        """Append a call record."""
        self._records.append(record)

    def get_run_cost(self) -> float:
        """Return total cost_usd for all recorded calls."""
        return sum(r.cost_usd for r in self._records)

    def get_agent_breakdown(self) -> dict[str, float]:
        """Return total cost per agent."""
        breakdown: dict[str, float] = {}
        for record in self._records:
            breakdown[record.agent] = breakdown.get(record.agent, 0.0) + record.cost_usd
        return breakdown

    def check_budget(self, budget_limit: float) -> bool:
        """Return True if total spend is under budget_limit, False otherwise."""
        return self.get_run_cost() <= budget_limit

    def get_records(self) -> list[LLMCallRecord]:
        """Return a copy of all call records."""
        return list(self._records)
