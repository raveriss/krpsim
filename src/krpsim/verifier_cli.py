"""Verifier command line interface."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .parser import ParseError
from .verifier import TraceError, verify_files


def build_parser() -> argparse.ArgumentParser:
    """Return the CLI argument parser."""

    parser = argparse.ArgumentParser(prog="krpsim-verif")
    parser.add_argument("config", help="configuration file path")
    parser.add_argument("trace", help="execution trace file path")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="enable verbose logging",
    )
    parser.add_argument("--log", help="file to write logs to")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the krpsim verifier."""

    parser = build_parser()
    args = parser.parse_args(argv)

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if args.log:
        handlers.append(logging.FileHandler(args.log))
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(message)s",
        handlers=handlers,
        force=True,
    )

    try:
        verify_files(Path(args.config), Path(args.trace))
    except (OSError, ParseError, TraceError) as exc:
        logging.error("invalid trace: %s", exc)
        print(f"invalid trace: {exc}")
        return 1
    logging.info("trace is valid")
    print("trace is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
