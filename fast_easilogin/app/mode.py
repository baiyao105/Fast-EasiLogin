from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass
class RunMode:
    mode: str  # "webui" | "service"
    log_level: str
    access_log: bool
    no_browser: bool


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--mode", choices=["webui", "service"], default="webui", help="启动模式: webui(WebUI模式) 或 service(服务模式)"
    )
    p.add_argument("--log-level", default="INFO")
    p.add_argument("--access-log", action="store_true")
    p.add_argument("--no-browser", action="store_true", help="WebUI模式下不自动打开浏览器")
    return p


def parse_mode(argv: list[str] | None = None) -> RunMode:
    args = build_parser().parse_args(argv)
    return RunMode(
        mode=args.mode,
        log_level=args.log_level.upper(),
        access_log=args.access_log,
        no_browser=args.no_browser,
    )
