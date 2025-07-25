"""Trace verification utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from krpsim.parser import Config, parse_file
from krpsim.simulator import Simulator


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


def _expected_trace(config: Config, max_time: int) -> tuple[list[TraceEntry], Simulator]:
    """Return the expected trace and simulator state for ``config``.

    The simulation is executed until ``max_time`` so that the verifier
    reproduces the exact conditions used to generate the provided trace.
    """

    sim = Simulator(config)
    raw = sim.run(max_time)
    entries = [TraceEntry(cycle, name) for cycle, name in raw]
    return entries, sim


def verify_trace(config: Config, trace: list[TraceEntry]) -> Simulator:
    """Validate ``trace`` against ``config``.

    Raises :class:`TraceError` at the first mismatch.
    """

    logger = logging.getLogger(__name__)

    if not trace:
        raise TraceError("empty trace")
    last = trace[-1]
    process = config.processes.get(last.process)
    if process is None:
        raise TraceError(f"unknown process '{last.process}' in trace")
    run_until = last.cycle + process.delay
    expected, sim = _expected_trace(config, run_until)
    for idx, (got, exp) in enumerate(zip(trace, expected), start=1):
        if got != exp:
            raise TraceError(
                f"line {idx}: expected {exp.cycle}:{exp.process} "
                f"but got {got.cycle}:{got.process}"
            )

    if len(trace) > len(expected):
        raise TraceError(f"trace has extra events starting at line {len(expected)+1}")

    logger.info("trace validated successfully")
    return sim

def verify_files(config_path: Path, trace_path: Path) -> Simulator:
    """Convenience wrapper verifying files."""

    logger = logging.getLogger(__name__)
    config = parse_file(config_path)
    trace = parse_trace(trace_path)
    logger.info("verifying trace against %s", config_path)
    return verify_trace(config, trace)
