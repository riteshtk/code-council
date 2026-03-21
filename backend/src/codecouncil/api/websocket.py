"""WebSocket debate event handler."""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from codecouncil.api.metrics import ws_connections

logger = logging.getLogger(__name__)


async def websocket_debate(websocket: WebSocket, run_id: str) -> None:
    """Handle a WebSocket connection for live debate events on *run_id*."""
    await websocket.accept()
    ws_connections.inc()
    logger.info("WebSocket connected for run %s", run_id)

    # Import runs store lazily to avoid circular imports
    from codecouncil.api.routes.runs import _runs

    run = _runs.get(run_id)
    if not run:
        await websocket.send_text(json.dumps({"type": "error", "detail": "Run not found"}))
        await websocket.close(code=4004, reason="Run not found")
        ws_connections.dec()
        return

    # Send a welcome / connection-acknowledged message
    await websocket.send_text(
        json.dumps({"type": "connected", "run_id": run_id})
    )

    last_seq = 0
    try:
        while True:
            # Re-fetch run in case it was updated
            run = _runs.get(run_id)
            if not run:
                break

            events = run.get("events", [])
            new_events = [e for e in events if e.get("sequence", 0) > last_seq]

            for event in new_events:
                await websocket.send_text(json.dumps(event))
                last_seq = event.get("sequence", last_seq)

            if run.get("status") in ("completed", "failed"):
                # Give a moment for any final events, then send them and close
                await asyncio.sleep(0.5)
                run = _runs.get(run_id)
                if run:
                    events = run.get("events", [])
                    final_new = [e for e in events if e.get("sequence", 0) > last_seq]
                    for event in final_new:
                        await websocket.send_text(json.dumps(event))
                await websocket.close(code=1000, reason="Run completed")
                break

            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for run %s", run_id)
    except Exception as exc:
        logger.exception("WebSocket error for run %s: %s", run_id, exc)
    finally:
        ws_connections.dec()
