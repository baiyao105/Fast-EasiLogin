from __future__ import annotations

import time
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class CapturedRequest:
    id: int
    method: str
    path: str
    query: str
    client: str
    headers: dict[str, str]
    body: Any
    body_raw: str | None
    status_code: int
    duration_ms: float
    created_at: float
    error: str | None = None


@dataclass
class ApiCaptureStore:
    """网关 API 请求捕获"""

    max_items: int = 200
    _items: deque[CapturedRequest] = field(default_factory=deque, init=False)
    _next_id: int = field(default=0, init=False)
    _enabled: bool = field(default=False, init=False)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    def add(
        self,
        *,
        method: str,
        path: str,
        query: str = "",
        client: str = "",
        headers: dict[str, str] | None = None,
        body: Any = None,
        body_raw: str | None = None,
        status_code: int = 200,
        duration_ms: float = 0.0,
        error: str | None = None,
    ) -> CapturedRequest:
        self._next_id += 1
        item = CapturedRequest(
            id=self._next_id,
            method=method.upper(),
            path=path,
            query=query,
            client=client,
            headers=headers or {},
            body=body,
            body_raw=body_raw,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            created_at=time.time(),
            error=error,
        )
        self._items.append(item)
        while len(self._items) > self.max_items:
            self._items.popleft()
        return item

    def list_items(self, limit: int = 100, path_contains: str | None = None) -> list[dict[str, Any]]:
        items = list(self._items)
        if path_contains:
            needle = path_contains.lower()
            items = [i for i in items if needle in i.path.lower()]
        items = items[-limit:]
        items.reverse()  # 最新在前
        return [asdict(i) for i in items]

    def clear(self) -> None:
        self._items.clear()
