"""In-process event bus for WebSocket broadcasting.

Simple queue per connection, managed by a singleton EventBus.
Uses thread-safe queue.Queue for cross-thread compatibility.
"""
from __future__ import annotations

import asyncio
import json
import queue
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class Event:
    event: str
    payload: dict[str, Any]
    sent_at: str

    def to_json(self) -> str:
        return json.dumps({"event": self.event, **self.payload, "sent_at": self.sent_at})


class EventBus:
    """Singleton event bus for broadcasting to WebSocket connections.

    Uses thread-safe queue.Queue for compatibility with both sync and async callers.
    """

    def __init__(self):
        self._queues: set[queue.Queue] = set()
        # Removed asyncio.Lock to avoid event loop issues in tests

    async def subscribe(self) -> queue.Queue:
        """Register a new subscriber and return their queue."""
        q: queue.Queue = queue.Queue()
        self._queues.add(q)
        return q

    async def unsubscribe(self, q: queue.Queue) -> None:
        """Unregister a subscriber."""
        self._queues.discard(q)

    async def publish(self, event: str, payload: dict[str, Any]) -> None:
        """Publish an event to all subscribers (async version)."""
        evt = Event(event=event, payload=payload, sent_at=datetime.now(timezone.utc).isoformat())
        for q in list(self._queues):
            try:
                q.put_nowait(evt)
            except queue.Full:
                pass

    async def broadcast(self, event: str, **kwargs: Any) -> None:
        """Convenience method to publish with keyword payload."""
        await self.publish(event, kwargs)

    def publish_sync(self, event: str, payload: dict[str, Any]) -> None:
        """Synchronously publish an event to all subscribers.
        
        Use this from synchronous endpoints (e.g., FastAPI sync routes).
        Thread-safe.
        """
        evt = Event(event=event, payload=payload, sent_at=datetime.now(timezone.utc).isoformat())
        for q in list(self._queues):
            try:
                q.put_nowait(evt)
            except queue.Full:
                pass

    def broadcast_sync(self, event: str, **kwargs: Any) -> None:
        """Synchronous convenience method."""
        self.publish_sync(event, kwargs)

    def _build_hello_event(self) -> "Event":
        return Event(event="hello", payload={"message": "connected to tv-backend stream"}, sent_at=datetime.now(timezone.utc).isoformat())


# Global singleton
event_bus = EventBus()


# Event payload builders per api-contract.md
def case_ingested_event(case_id: str, violation_type: str, camera_id: str, occurred_at: str) -> dict:
    return {
        "case_id": case_id,
        "violation_type": violation_type,
        "camera_id": camera_id,
        "occurred_at": occurred_at,
    }


def case_reviewed_event(case_id: str, decision: str, reviewer_id: str | None) -> dict:
    return {
        "case_id": case_id,
        "decision": decision,
        "reviewer_id": reviewer_id,
    }


def challan_issued_event(challan_id: str, case_id: str, channel: str) -> dict:
    return {
        "challan_id": challan_id,
        "case_id": case_id,
        "channel": channel,
    }


def heartbeat_event() -> dict:
    return {}