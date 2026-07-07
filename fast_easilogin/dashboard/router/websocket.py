import asyncio
import json
import time as _time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from fast_easilogin.api.gateway.state import get_login_trends, get_recent_logins, get_stats
from fast_easilogin.storage import load_appsettings_model

router = APIRouter(tags=["websocket"])

_clients: set[WebSocket] = set()
_push_task: asyncio.Task | None = None
_lock = asyncio.Lock()
_shutdown = False


async def _broadcast_stats():
    """定期推统计数据"""
    while not _shutdown:
        async with _lock:
            clients_snapshot = list(_clients)

        if not clients_snapshot:
            await asyncio.sleep(1)
            continue

        try:
            data = _build_stats_message()
            message = json.dumps(data, ensure_ascii=False)
            disconnected: list[WebSocket] = []
            for client in clients_snapshot:
                try:
                    await client.send_text(message)
                except Exception:
                    disconnected.append(client)

            if disconnected:
                async with _lock:
                    _clients.difference_update(disconnected)
        except Exception as e:
            logger.debug("广播统计数据失败: {}", e)

        await asyncio.sleep(1)


def _build_stats_message() -> dict[str, Any]:
    """统计数据"""
    stats = get_stats()
    settings = load_appsettings_model()
    return {
        "type": "stats",
        "data": {
            "service_status": "running",
            "uptime_seconds": int(_time.time() - stats["start_time"]),
            "listen_port": settings.Global.port,
            "total_logins": stats["total_logins"],
            "success_logins": stats["success_logins"],
            "failed_logins": stats["failed_logins"],
        },
    }


def _build_recent_logins_message(limit: int = 20) -> dict[str, Any]:
    """最近登录"""
    records = get_recent_logins(limit)
    return {
        "type": "recent_logins",
        "data": records,
    }


def _build_login_trends_message(hours: int = 24) -> dict[str, Any]:
    """登录趋势"""
    trends = get_login_trends(hours)
    return {
        "type": "login_trends",
        "data": trends,
    }


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点"""
    global _push_task  # noqa: PLW0603

    try:
        await websocket.accept()
    except Exception:
        return

    async with _lock:
        _clients.add(websocket)

    logger.debug("WebSocket连接, 连接数: {}", len(_clients))

    if _push_task is None or _push_task.done():
        _push_task = asyncio.create_task(_broadcast_stats())

    try:
        try:
            await websocket.send_text(json.dumps(_build_stats_message(), ensure_ascii=False))
            await websocket.send_text(json.dumps(_build_recent_logins_message(), ensure_ascii=False))
        except Exception:
            return

        while True:
            try:
                data = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception:
                break

            try:
                msg = json.loads(data)
                if msg.get("type") == "get_recent_logins":
                    limit = msg.get("limit", 20)
                    await websocket.send_text(json.dumps(_build_recent_logins_message(limit), ensure_ascii=False))
                elif msg.get("type") == "get_login_trends":
                    hours = msg.get("hours", 24)
                    await websocket.send_text(json.dumps(_build_login_trends_message(hours), ensure_ascii=False))
            except json.JSONDecodeError:
                pass
            except Exception:
                break
    finally:
        async with _lock:
            _clients.discard(websocket)
        logger.debug("WebSocket断开, 连接数: {}", len(_clients))
