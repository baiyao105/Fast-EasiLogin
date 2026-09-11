from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request

from fast_easilogin.dashboard.v1.auth import require_dashboard_auth
from fast_easilogin.dashboard.v1.models import LoginEvent, LoginEventSummary, Page
from fast_easilogin.storage.repositories.login_events import (
    list_login_events,
    prune_login_events,
    summarize_login_events,
    trend_login_events,
)

router = APIRouter(prefix="/login-events", tags=["login-events"], dependencies=[Depends(require_dashboard_auth)])
MAX_PAGE_SIZE = 100
MAX_TREND_HOURS = 168


def _dto(event) -> LoginEvent:
    return LoginEvent.model_validate(event, from_attributes=True)


@router.get("", response_model=Page[LoginEvent])
async def list_events(
    request: Request, page: int = 1, page_size: int = 20, status: str | None = None, user_id: str | None = None
):
    if page < 1 or page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise HTTPException(status_code=422, detail="invalid_pagination")
    async with request.app.state.db_factory() as db:
        events, total = await list_login_events(db, page=page, page_size=page_size, status=status, user_id=user_id)
    return Page(items=[_dto(event) for event in events], page=page, page_size=page_size, total=total)


@router.get("/summary", response_model=LoginEventSummary)
async def summary(request: Request, hours: int = 24):
    async with request.app.state.db_factory() as db:
        return LoginEventSummary(
            counts=await summarize_login_events(db, since=datetime.now(UTC) - timedelta(hours=hours))
        )


@router.get("/trends")
async def trends(request: Request, hours: int = 24):
    if hours < 1 or hours > MAX_TREND_HOURS:
        raise HTTPException(status_code=422, detail="invalid_hours")
    since = datetime.now(UTC) - timedelta(hours=hours)
    async with request.app.state.db_factory() as db:
        return await trend_login_events(db, since=since, hours=hours)


@router.delete("")
async def prune(before: datetime, request: Request):
    async with request.app.state.db_factory() as db:
        deleted = await prune_login_events(db, before=before)
        await db.commit()
    return {"deleted": deleted}
