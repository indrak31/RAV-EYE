"""WS /api/stream — real-time dashboard stream.

Day 1: stubbed — accepts the connection, sends a `hello` event, then closes
with code 1011 carrying a `not_implemented` event.
Planned: D5-7 — see docs/api-contract.md section 7.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket

router = APIRouter(prefix="/api", tags=["stream"])


@router.websocket("/stream")
async def stream(ws: WebSocket) -> None:
    await ws.accept()
    await ws.send_text(
        json.dumps({"event": "hello", "planned_day": "D5-7", "detail": "not_implemented"})
    )
    await ws.send_text(json.dumps({"event": "not_implemented", "planned_day": "D5-7"}))
    await ws.close(code=1011, reason="not implemented until D5-7")
