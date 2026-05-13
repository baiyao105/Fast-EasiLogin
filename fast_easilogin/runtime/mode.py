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
    p = argparse.ArgumentParser()
    p.add_argument("--services", choices=["install", "uninstall"])
    p.add_argument("--log-level", default="INFO")
    p.add_argument("--access-log", action="store_true")
    p.add_argument("--service-mode", action="store_true")
    return p


def parse_mode(argv: list[str] | None = None) -> RunMode:
    args = build_parser().parse_args(argv)
    return RunMode(
        api=True,
        console=not args.service_mode,
        services=args.services,
        log_level=args.log_level.upper(),
        access_log=args.access_log,
    )
