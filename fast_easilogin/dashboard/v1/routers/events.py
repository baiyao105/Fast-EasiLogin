from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import StreamingResponse

from fast_easilogin.dashboard.v1.auth import require_dashboard_auth

router = APIRouter(tags=["events"], dependencies=[Depends(require_dashboard_auth)])


@router.get("/events")
async def stream(request: Request, last_event_id: str | None = Header(default=None, alias="Last-Event-ID")):
    bus = request.app.state.services.event_bus
    try:
        queue = await bus.subscribe(int(last_event_id) if last_event_id and last_event_id.isdigit() else None)
    except RuntimeError:
        return StreamingResponse(iter(()), media_type="text/event-stream")

    async def generate():
        try:
            yield "event: service.snapshot\ndata: " + json.dumps({"status": "running"}) + "\n\n"
            while True:
                try:
                    if await request.is_disconnected():
                        break
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    if event is None:
                        break
                    yield f"id: {event.id}\nevent: {event.type}\ndata: {json.dumps(event.data)}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            await bus.unsubscribe(queue)

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})
