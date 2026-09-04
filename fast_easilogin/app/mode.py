from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass
class RunMode:
    only_service: bool
    log_level: str
    access_log: bool
    no_browser: bool


def service_argv(argv: list[str]) -> list[str]:
    supported = {"--only-service", "--access-log", "--no-browser"}
    result: list[str] = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg in supported:
            result.append(arg)
        elif arg == "--log-level" and index + 1 < len(argv):
            result.extend((arg, argv[index + 1]))
            index += 1
        index += 1
    return result


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--only-service", action="store_true", help="只运行api")
    p.add_argument("--log-level", default="INFO")
    p.add_argument("--access-log", action="store_true")
    p.add_argument("--no-browser", action="store_true", help="WebUI模式下不自动打开浏览器")
    return p


def parse_mode(argv: list[str] | None = None) -> RunMode:
    args = build_parser().parse_args(argv)
    return RunMode(
        only_service=args.only_service,
        log_level=args.log_level.upper(),
        access_log=args.access_log,
        no_browser=args.no_browser,
    )
