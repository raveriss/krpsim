"""Command line interface for krpsim."""

from __future__ import annotations

import argparse
import logging
import os
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
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="enable verbose logging",
    )
    parser.add_argument(
        "--log",
        help="path to write logs to",
    )
    return parser


def _validate_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Validate CLI arguments."""

    config_path = Path(args.config)
    if ".." in config_path.parts:
        parser.error("path traversal detected in config path")
    if not config_path.is_file():
        parser.error(f"invalid config path: '{args.config}'")
    if not os.access(config_path, os.R_OK):
        parser.error(f"config file is not readable: '{args.config}'")
    if args.delay <= 0:
        parser.error("delay must be a positive integer")


def _run_simulation(args: argparse.Namespace) -> Simulator:
    """Run the simulation and return the simulator instance."""

    config = parser_mod.parse_file(Path(args.config))
    sim = Simulator(config)
    print_header(config)
    trace = sim.run(args.delay)
    for line in format_trace(trace):
        print(line)
    save_trace(trace, Path(args.trace))
    return sim


def main(argv: list[str] | None = None) -> int:
    """Entry point for the krpsim CLI."""

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

    _validate_args(args, parser)

    sim = _run_simulation(args)

    exit_code = 0
    if sim.time >= args.delay:
        print(f"max time reached at time {sim.time}")
        exit_code = 1
    elif sim.deadlock:
        print(f"deadlock detected at time {sim.time}")
        exit_code = 1
    else:
        print(f"no more process doable at time {sim.time}")
    print("Stock:")
    for name, qty in sim.stocks.items():
        print(f"{name} => {qty}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
