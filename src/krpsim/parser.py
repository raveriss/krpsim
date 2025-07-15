"""KRPSIM configuration parser (Agent 1)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Process:
    """Representation of a process."""

    name: str
    needs: dict[str, int]
    results: dict[str, int]
    delay: int


@dataclass
class Config:
    """Parsed configuration."""

    stocks: dict[str, int]
    processes: dict[str, Process]


class ParseError(Exception):
    """Raised when the configuration is invalid."""


def _parse_stock(line: str) -> tuple[str, int]:
    try:
        name, qty = line.split(":", 1)
    except ValueError as exc:
        raise ParseError(f"invalid stock line: '{line}'") from exc
    if not name or not qty.isdigit():
        raise ParseError(f"invalid stock line: '{line}'")
    quantity = int(qty)
    if quantity < 0:
        raise ParseError(f"invalid stock quantity in line: '{line}'")
    return name, quantity


def _parse_resources(block: str) -> dict[str, int]:
    resources: dict[str, int] = {}
    if not block:
        return resources
    for item in block.split(";"):
        if not item:
            continue
        name, qty = item.split(":", 1)
        if not qty.isdigit():
            raise ParseError(f"invalid quantity for resource '{item}'")
        resources[name] = int(qty)
    return resources


def _parse_process(line: str) -> Process:
    match = re.match(r"^([^:]+):\(([^)]*)\):\(([^)]*)\):(\d+)$", line)
    if not match:
        raise ParseError(f"invalid process line: '{line}'")
    name, needs_block, results_block, delay_str = match.groups()
    needs = _parse_resources(needs_block)
    results = _parse_resources(results_block)
    return Process(name=name, needs=needs, results=results, delay=int(delay_str))


def parse_file(path: Path) -> Config:
    """Parse a configuration file and return a :class:`Config`."""

    text = path.read_text().splitlines()
    stocks: dict[str, int] = {}
    processes: dict[str, Process] = {}
    for line in text:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("optimize:"):
            # optimization settings are currently ignored
            continue
        if ":(" in line:
            process = _parse_process(line)
            if process.name in processes:
                raise ParseError(f"duplicate process '{process.name}'")
            processes[process.name] = process
        elif ":" in line:
            name, qty = _parse_stock(line)
            if name in stocks:
                raise ParseError(f"duplicate stock '{name}'")
            stocks[name] = qty
        else:
            raise ParseError(f"unrecognized line: '{line}'")
    if not stocks or not processes:
        raise ParseError("configuration must define at least one stock and process")
    return Config(stocks=stocks, processes=processes)
