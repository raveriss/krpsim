"""Trace verification utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .parser import Config, parse_file
from .simulator import Simulator


class TraceError(Exception):
    """Raised when a trace is invalid."""


@dataclass
class TraceEntry:
    cycle: int
    process: str


def parse_trace(path: Path) -> list[TraceEntry]:
    """Return trace entries parsed from ``path``."""

    logger = logging.getLogger(__name__)
    lines = path.read_text().splitlines()
    entries: list[TraceEntry] = []
    for idx, line in enumerate(lines, start=1):
        if not line:
            raise TraceError(f"empty trace line {idx}")
        if ":" not in line:
            raise TraceError(f"invalid trace line {idx}: '{line}'")
        cycle_str, name = line.split(":", 1)
        if not cycle_str.isdigit():
            raise TraceError(f"invalid trace line {idx}: '{line}'")
        entry = TraceEntry(int(cycle_str), name)
        logger.info("%d:%s", entry.cycle, entry.process)
        entries.append(entry)
    return entries


def _expected_trace(config: Config) -> list[TraceEntry]:
    sim = Simulator(config)
    raw = sim.run(10_000)
    return [TraceEntry(cycle, name) for cycle, name in raw]


def verify_trace(config: Config, trace: list[TraceEntry]) -> None:
    """Validate ``trace`` against ``config``.

    Raises :class:`TraceError` at the first mismatch.
    """

    logger = logging.getLogger(__name__)
    expected = _expected_trace(config)
    for idx, (got, exp) in enumerate(zip(trace, expected), start=1):
        if got != exp:
            raise TraceError(
                f"line {idx}: expected {exp.cycle}:{exp.process} "
                f"but got {got.cycle}:{got.process}"
            )

    if len(trace) < len(expected):
        missing = expected[len(trace)]
        raise TraceError(
            f"trace ended early at line {len(trace)+1}, "
            f"expected {missing.cycle}:{missing.process}"
        )

    if len(trace) > len(expected):
        raise TraceError(f"trace has extra events starting at line {len(expected)+1}")

    logger.info("trace validated successfully")


def verify_files(config_path: Path, trace_path: Path) -> None:
    """Convenience wrapper verifying files."""

    logger = logging.getLogger(__name__)
    config = parse_file(config_path)
    trace = parse_trace(trace_path)
    logger.info("verifying trace against %s", config_path)
    verify_trace(config, trace)
