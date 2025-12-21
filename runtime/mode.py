import argparse
from dataclasses import dataclass


@dataclass
class RunMode:
    api: bool
    console: bool
    services: str | None
    log_level: str
    access_log: bool


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--services", choices=["install", "uninstall"], default=None)
    p.add_argument("--log-level", default="INFO")
    p.add_argument("--log-access", choices=["on", "off"], default="off")
    p.add_argument("--service-mode", action="store_true")
    return p


def parse_mode(argv: list[str] | None = None) -> RunMode:
    args = build_parser().parse_args(argv)
    api = True
    console = not bool(getattr(args, "service_mode", False))
    services = getattr(args, "services", None)
    log_level = str(getattr(args, "log_level", "INFO") or "INFO")
    access_log = bool(getattr(args, "log_access", "off") == "on")
    return RunMode(api=api, console=console, services=services, log_level=log_level, access_log=access_log)
