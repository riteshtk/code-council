"""Prometheus metrics for CodeCouncil."""
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

runs_total = Counter(
    "codecouncil_runs_total",
    "Total runs",
    ["status"],
)

runs_active = Gauge(
    "codecouncil_runs_active",
    "Active runs",
)

llm_duration = Histogram(
    "codecouncil_llm_call_duration_seconds",
    "LLM call duration",
    ["provider", "model"],
)

tokens_total = Counter(
    "codecouncil_tokens_total",
    "Tokens used",
    ["provider", "model", "direction"],
)

cost_total = Counter(
    "codecouncil_cost_usd_total",
    "Cost in USD",
    ["provider", "model"],
)

ws_connections = Gauge(
    "codecouncil_websocket_connections",
    "Active WebSocket connections",
)


async def metrics_endpoint(request):
    """Expose Prometheus metrics."""
    from starlette.responses import Response
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
