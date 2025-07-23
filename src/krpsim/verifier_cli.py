"""Verifier command line interface."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .parser import ParseError, parse_file
from .simulator import Simulator
from .verifier import TraceError, verify_files


def build_parser() -> argparse.ArgumentParser:
    """Return the CLI argument parser."""

    parser = argparse.ArgumentParser(prog="krpsim_verif")
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

    cfg = parse_file(Path(args.config))

    sim = Simulator(cfg)
    sim.run(10_000)

    exit_code = 0
    try:
        verify_files(Path(args.config), Path(args.trace))
    except (OSError, ParseError, TraceError) as exc:
        logging.error("invalid trace: %s", exc)
        print(f"invalid trace: {exc}")
        exit_code = 1
    else:
        logging.info("trace is valid")
        print("trace is valid")

    stock_names = sorted(sim.config.all_stock_names())
    max_len = max((len(name) for name in stock_names), default=0)
    print("Final Stocks:")
    for name in stock_names:
        print(f"  {name:<{max_len}}  => {sim.stocks.get(name, 0)}")
    print(f"Last cycle: {sim.time}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
