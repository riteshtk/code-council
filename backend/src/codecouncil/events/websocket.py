"""WebSocketPublisher — manages WebSocket connections per run_id and publishes events."""

import json
from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket

from codecouncil.models.events import Event


class WebSocketPublisher:
    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)

    def add_connection(self, run_id: UUID, ws: WebSocket) -> None:
        self._connections[run_id].add(ws)

    def remove_connection(self, run_id: UUID, ws: WebSocket) -> None:
        self._connections[run_id].discard(ws)
        if not self._connections[run_id]:
            del self._connections[run_id]

    async def handle(self, event: Event) -> None:
        """Send event to all WebSocket clients subscribed to this run."""
        connections = self._connections.get(event.run_id, set())
        if not connections:
            return

        data = json.dumps({
            "event_id": str(event.event_id),
            "run_id": str(event.run_id),
            "sequence": event.sequence,
            "agent": event.agent,
            "event_type": event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type),
            "phase": event.phase.value if hasattr(event.phase, "value") else str(event.phase),
            "round": event.round,
            "content": event.content,
            "structured": event.structured,
            "timestamp": event.timestamp.isoformat(),
            "metadata": {
                "provider": event.metadata.provider,
                "model": event.metadata.model,
                "input_tokens": event.metadata.input_tokens,
                "output_tokens": event.metadata.output_tokens,
                "cost_usd": event.metadata.cost_usd,
                "latency_ms": event.metadata.latency_ms,
                "cached": event.metadata.cached,
                "fallback": event.metadata.fallback,
            },
        })

        disconnected: set[WebSocket] = set()
        for ws in connections:
            try:
                await ws.send_text(data)
            except Exception:
                disconnected.add(ws)

        for ws in disconnected:
            self.remove_connection(event.run_id, ws)

    def get_connection_count(self, run_id: UUID | None = None) -> int:
        if run_id:
            return len(self._connections.get(run_id, set()))
        return sum(len(conns) for conns in self._connections.values())
