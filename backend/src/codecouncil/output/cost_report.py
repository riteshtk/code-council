"""Cost report generator from council events."""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class AgentCostEntry:
    agent: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int


def generate_cost_report(state: dict) -> dict:
    """Generate per-agent cost breakdown from events."""
    aggregated: dict[str, dict] = {}

    for event in state.get("events", []):
        if event.get("event_type") != "agent_speaking":
            continue
        meta = event.get("metadata", {})
        agent = event.get("agent", "unknown")

        if agent not in aggregated:
            aggregated[agent] = {
                "agent": agent,
                "provider": meta.get("provider", ""),
                "model": meta.get("model", ""),
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "latency_ms": 0,
            }

        agg = aggregated[agent]
        agg["input_tokens"] += meta.get("input_tokens", 0)
        agg["output_tokens"] += meta.get("output_tokens", 0)
        agg["cost_usd"] += meta.get("cost_usd", 0.0)
        agg["latency_ms"] += meta.get("latency_ms", 0)
        # Keep the latest provider/model (they should be consistent per agent)
        if meta.get("provider"):
            agg["provider"] = meta["provider"]
        if meta.get("model"):
            agg["model"] = meta["model"]

    entries = [AgentCostEntry(**v) for v in aggregated.values()]

    total_input = sum(e.input_tokens for e in entries)
    total_output = sum(e.output_tokens for e in entries)
    total_cost = sum(e.cost_usd for e in entries)
    total_latency = sum(e.latency_ms for e in entries)

    return {
        "agents": [asdict(e) for e in entries],
        "total": {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "cost_usd": total_cost,
            "latency_ms": total_latency,
        },
    }
