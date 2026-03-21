"""Server-Sent Events stream for debate events."""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from fastapi import Request
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)


async def _event_generator(request: Request, run_id: str) -> AsyncIterator[dict]:
    """
    Yield SSE events for *run_id*.

    Supports ``Last-Event-ID`` header for reconnect — resumes from the sequence
    number embedded in the last-event-id.
    """
    last_event_id_raw = request.headers.get("last-event-id", "0")
    try:
        last_sequence = int(last_event_id_raw)
    except (ValueError, TypeError):
        last_sequence = 0

    # Send a connection-established heartbeat
    yield {
        "id": str(last_sequence),
        "event": "connected",
        "data": json.dumps({"run_id": run_id, "resumed_from": last_sequence}),
    }

    # In a full implementation we'd subscribe to the EventBus here and
    # stream live events.  For now we yield a single "no_events" sentinel
    # so that the endpoint is functional without a running graph.
    yield {
        "id": str(last_sequence + 1),
        "event": "no_events",
        "data": json.dumps({"run_id": run_id, "message": "No events yet"}),
    }


async def sse_stream(request: Request, run_id: str) -> EventSourceResponse:
    """SSE endpoint — streams debate events for *run_id*."""
    return EventSourceResponse(_event_generator(request, run_id))
