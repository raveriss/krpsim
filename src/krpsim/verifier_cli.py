"""Verifier command line interface."""

from __future__ import annotations

import argparse
from pathlib import Path

from .parser import ParseError
from .verifier import TraceError, verify_files


def build_parser() -> argparse.ArgumentParser:
    """Return the CLI argument parser."""

    parser = argparse.ArgumentParser(prog="krpsim-verif")
    parser.add_argument("config", help="configuration file path")
    parser.add_argument("trace", help="execution trace file path")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the krpsim verifier."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        verify_files(Path(args.config), Path(args.trace))
    except (OSError, ParseError, TraceError) as exc:
        print(f"invalid trace: {exc}")
        return 1
    print("trace is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
