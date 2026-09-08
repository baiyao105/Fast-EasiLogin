from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DomainEvent:
    id: int
    type: str
    data: dict[str, Any]


class EventBus:
    def __init__(self, history_size: int = 256) -> None:
        self._next_id = 0
        self._subscribers: set[asyncio.Queue[DomainEvent | None]] = set()
        self._history: deque[DomainEvent] = deque(maxlen=history_size)
        self._lock = asyncio.Lock()
        self._closed = False

    async def publish(self, event_type: str, data: dict[str, Any]) -> DomainEvent:
        async with self._lock:
            self._next_id += 1
            event = DomainEvent(self._next_id, event_type, data)
            self._history.append(event)
            for queue in tuple(self._subscribers):
                queue.put_nowait(event)
            return event

    async def subscribe(self, last_event_id: int | None = None) -> asyncio.Queue[DomainEvent | None]:
        queue: asyncio.Queue[DomainEvent | None] = asyncio.Queue()
        async with self._lock:
            if self._closed:
                raise RuntimeError("event_bus_closed")
            if last_event_id is not None:
                for event in self._history:
                    if event.id > last_event_id:
                        queue.put_nowait(event)
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[DomainEvent | None]) -> None:
        async with self._lock:
            self._subscribers.discard(queue)

    async def close(self) -> None:
        async with self._lock:
            self._closed = True
            for queue in tuple(self._subscribers):
                queue.put_nowait(None)
            self._subscribers.clear()
