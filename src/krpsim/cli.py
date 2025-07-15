"""Command line interface for krpsim."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """Return the CLI argument parser."""

    parser = argparse.ArgumentParser(prog="krpsim")
    parser.add_argument("config", help="configuration file path")
    parser.add_argument(
        "delay",
        type=int,
        help="maximum delay allowed (positive integer)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the krpsim CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    if not config_path.is_file():
        parser.error(f"invalid config path: '{args.config}'")

    if args.delay <= 0:
        parser.error("delay must be a positive integer")

    print("krpsim", args.config, args.delay)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
