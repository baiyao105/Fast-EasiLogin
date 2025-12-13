from __future__ import annotations


def deprecated_field(name: str, *, replacement: str | None = None):
    def _cls_decorator(cls: type) -> type:
        info = getattr(cls, "_deprecated_fields", {})
        info[name] = {"replacement": replacement}
        cls._deprecated_fields = info
        return cls

    return _cls_decorator
