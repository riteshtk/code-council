"""SSEPublisher — Server-Sent Events publisher for streaming events to HTTP clients."""

import asyncio
import json
from collections import defaultdict
from uuid import UUID

from codecouncil.models.events import Event


class SSEPublisher:
    def __init__(self) -> None:
        self._queues: dict[UUID, list[asyncio.Queue]] = defaultdict(list)

    def add_subscriber(self, run_id: UUID) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._queues[run_id].append(queue)
        return queue

    def remove_subscriber(self, run_id: UUID, queue: asyncio.Queue) -> None:
        if run_id in self._queues:
            self._queues[run_id] = [q for q in self._queues[run_id] if q is not queue]
            if not self._queues[run_id]:
                del self._queues[run_id]

    async def handle(self, event: Event) -> None:
        """Push event to all SSE subscriber queues for this run."""
        queues = self._queues.get(event.run_id, [])
        data = json.dumps({
            "event_id": str(event.event_id),
            "run_id": str(event.run_id),
            "sequence": event.sequence,
            "agent": event.agent,
            "event_type": event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type),
            "phase": event.phase.value if hasattr(event.phase, "value") else str(event.phase),
            "round": event.round,
            "content": event.content,
            "timestamp": event.timestamp.isoformat(),
        })
        for queue in queues:
            await queue.put(data)
