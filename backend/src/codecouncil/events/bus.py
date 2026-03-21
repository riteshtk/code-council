"""EventBus — central fan-out hub for all CodeCouncil events."""

import asyncio
from collections import defaultdict
from typing import AsyncIterator, Callable, Awaitable
from uuid import UUID

from codecouncil.models.events import Event


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[UUID, list[asyncio.Queue]] = defaultdict(list)
        self._handlers: list[Callable[[Event], Awaitable[None]]] = []
        self._sequence_counters: dict[UUID, int] = defaultdict(int)
        self._event_history: dict[UUID, list[Event]] = defaultdict(list)

    async def emit(self, event: Event) -> None:
        """Emit an event. Assigns sequence number, fans out to all subscribers + handlers."""
        # Assign monotonically increasing sequence per run_id
        self._sequence_counters[event.run_id] += 1
        event.sequence = self._sequence_counters[event.run_id]

        # Store in history for replay
        self._event_history[event.run_id].append(event)

        # Fan out to handlers (persistence, websocket, sse, redis, webhook)
        handler_tasks = [handler(event) for handler in self._handlers]
        if handler_tasks:
            await asyncio.gather(*handler_tasks, return_exceptions=True)

        # Fan out to subscribers
        for queue in self._subscribers[event.run_id]:
            await queue.put(event)

    async def subscribe(self, run_id: UUID) -> AsyncIterator[Event]:
        """Subscribe to events for a run. Returns async iterator."""
        queue: asyncio.Queue[Event] = asyncio.Queue()
        self._subscribers[run_id].append(queue)
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self._subscribers[run_id].remove(queue)

    async def replay(self, run_id: UUID, after_sequence: int = 0) -> list[Event]:
        """Replay events for a run after a given sequence number."""
        return [e for e in self._event_history.get(run_id, []) if e.sequence > after_sequence]

    def add_handler(self, handler: Callable[[Event], Awaitable[None]]) -> None:
        """Register a handler that receives all events."""
        self._handlers.append(handler)

    def remove_handler(self, handler: Callable[[Event], Awaitable[None]]) -> None:
        """Remove a handler."""
        self._handlers.remove(handler)

    def get_sequence(self, run_id: UUID) -> int:
        """Get current sequence number for a run."""
        return self._sequence_counters.get(run_id, 0)

    def clear_run(self, run_id: UUID) -> None:
        """Clean up all state for a completed run."""
        self._subscribers.pop(run_id, None)
        self._event_history.pop(run_id, None)
        self._sequence_counters.pop(run_id, None)
