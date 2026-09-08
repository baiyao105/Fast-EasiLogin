from __future__ import annotations

from fastapi import Request

from fast_easilogin.core.services import Services


def services(request: Request) -> Services:
    return request.app.state.services
