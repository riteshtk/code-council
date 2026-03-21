"""WebSocket debate event handler."""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from codecouncil.api.metrics import ws_connections

logger = logging.getLogger(__name__)

_PING_INTERVAL = 15  # seconds


async def websocket_debate(websocket: WebSocket, run_id: str) -> None:
    """Handle a WebSocket connection for live debate events on *run_id*."""
    await websocket.accept()
    ws_connections.inc()
    logger.info("WebSocket connected for run %s", run_id)

    async def _ping_loop():
        """Send a ping frame every PING_INTERVAL seconds."""
        while True:
            await asyncio.sleep(_PING_INTERVAL)
            try:
                await websocket.send_text(json.dumps({"type": "ping"}))
            except Exception:
                break

    ping_task = asyncio.create_task(_ping_loop())

    try:
        # Send a welcome / connection-acknowledged message
        await websocket.send_text(
            json.dumps({"type": "connected", "run_id": run_id})
        )

        # Main receive loop — handle incoming client messages
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=_PING_INTERVAL + 5)
            except asyncio.TimeoutError:
                continue

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "detail": "Invalid JSON"})
                )
                continue

            msg_type = msg.get("type", "")

            if msg_type == "pong":
                # Client responding to our ping — do nothing
                pass
            elif msg_type == "human_challenge":
                # Forward to the run's event bus (stubbed here)
                logger.info("Human challenge received for run %s: %s", run_id, msg)
                await websocket.send_text(
                    json.dumps({"type": "ack", "original_type": "human_challenge"})
                )
            else:
                await websocket.send_text(
                    json.dumps({"type": "error", "detail": f"Unknown message type '{msg_type}'"})
                )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for run %s", run_id)
    except Exception as exc:
        logger.exception("WebSocket error for run %s: %s", run_id, exc)
    finally:
        ping_task.cancel()
        ws_connections.dec()
