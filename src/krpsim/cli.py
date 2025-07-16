"""Command line interface for krpsim."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import parser as parser_mod
from .display import format_trace, print_header, save_trace
from .simulator import Simulator


def build_parser() -> argparse.ArgumentParser:
    """Return the CLI argument parser."""

    parser = argparse.ArgumentParser(prog="krpsim")
    parser.add_argument("config", help="configuration file path")
    parser.add_argument(
        "delay",
        type=int,
        help="maximum delay allowed (positive integer)",
    )
    parser.add_argument(
        "--trace",
        default="trace.txt",
        help="path of the file to write machine trace to",
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

    config = parser_mod.parse_file(config_path)
    sim = Simulator(config)

    print_header(config)
    trace = sim.run(args.delay)
    for line in format_trace(trace):
        print(line)

    if sim.time >= args.delay:
        print(f"max time reached at time {sim.time}")
    else:
        print(f"no more process doable at time {sim.time}")
    print("Stock:")
    for name, qty in sim.stocks.items():
        print(f"{name} => {qty}")

    save_trace(trace, Path(args.trace))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
