"""WS /api/stream — real-time dashboard stream.

Day 5-7: implemented with in-process pub/sub via EventBus.
Event types: case.ingested, case.reviewed, challan.issued, heartbeat (every 30s).
"""
from __future__ import annotations

import asyncio
import os
import queue

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.event_bus import event_bus

router = APIRouter(prefix="/api", tags=["stream"])

# Heartbeat interval - can be overridden via env for testing
HEARTBEAT_INTERVAL = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))


@router.websocket("/stream")
async def stream(ws: WebSocket) -> None:
    await ws.accept()

    # Subscribe to event bus
    q = await event_bus.subscribe()

    # Send hello event
    hello_event = event_bus._build_hello_event()
    await ws.send_text(hello_event.to_json())

    # Helper to send heartbeat
    async def send_heartbeat():
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            try:
                await ws.send_text('{"event": "heartbeat"}')
            except Exception:
                break

    heartbeat_task = asyncio.create_task(send_heartbeat())

    try:
        # Listen for events from queue and forward to WebSocket
        while True:
            try:
                event = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, q.get),
                    timeout=5.0,
                )
            except asyncio.TimeoutError:
                continue
            except queue.Empty:
                continue

            try:
                await ws.send_text(event.to_json())
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        heartbeat_task.cancel()
        await event_bus.unsubscribe(q)
        try:
            await ws.close()
        except Exception:
            pass