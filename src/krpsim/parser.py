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
    optimize: list[str] | None = None


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
        quantity = int(qty)
        if quantity <= 0:
            raise ParseError(f"invalid quantity for resource '{item}'")
        if name in resources:
            raise ParseError(f"duplicate resource '{name}' in '{block}'")
        resources[name] = quantity
    return resources


def _parse_process(line: str) -> Process:
    match = re.match(r"^([^:]+):\(([^)]*)\):\(([^)]*)\):(\d+)$", line)
    if not match:
        raise ParseError(f"invalid process line: '{line}'")
    name, needs_block, results_block, delay_str = match.groups()
    needs = _parse_resources(needs_block)
    results = _parse_resources(results_block)
    return Process(
        name=name,
        needs=needs,
        results=results,
        delay=int(delay_str),
    )


def _parse_optimize(line: str) -> list[str]:
    match = re.match(r"^optimize:\(([^)]*)\)$", line)
    if not match:
        raise ParseError(f"invalid optimize line: '{line}'")
    block = match.group(1)
    items = [item for item in block.split(";") if item]
    if not items:
        raise ParseError(f"invalid optimize line: '{line}'")
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            raise ParseError(f"duplicate optimize target '{item}'")
        seen.add(item)
        result.append(item)
    return result


def _handle_optimize(line: str, optimize: list[str] | None) -> list[str] | None:
    if optimize is not None:
        raise ParseError("duplicate optimize line")
    return _parse_optimize(line)


def _handle_process(line: str, processes: dict[str, Process]) -> None:
    process = _parse_process(line)
    if process.name in processes:
        raise ParseError(f"duplicate process '{process.name}'")
    processes[process.name] = process


def _handle_stock(line: str, stocks: dict[str, int]) -> None:
    name, qty = _parse_stock(line)
    if name in stocks:
        raise ParseError(f"duplicate stock '{name}'")
    stocks[name] = qty


def _validate_optimize(
    optimize: list[str], stocks: dict[str, int], processes: dict[str, Process]
) -> None:
    known: set[str] = set(stocks)
    for proc in processes.values():
        known.update(proc.needs)
        known.update(proc.results)
    for item in optimize:
        if item != "time" and item not in known:
            raise ParseError(f"unknown stock '{item}' in optimize line")


def parse_file(path: Path) -> Config:
    """Parse a configuration file and return a :class:`Config`."""

    text = path.read_text().splitlines()
    stocks: dict[str, int] = {}
    processes: dict[str, Process] = {}
    optimize: list[str] | None = None
    for line in text:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("optimize:"):
            optimize = _handle_optimize(line, optimize)
        elif ":(" in line:
            _handle_process(line, processes)
        elif ":" in line:
            _handle_stock(line, stocks)
        else:
            raise ParseError(f"unrecognized line: '{line}'")
    if not stocks or not processes:
        raise ParseError("configuration must define at least one stock and process")
    if optimize:
        _validate_optimize(optimize, stocks, processes)
    return Config(stocks=stocks, processes=processes, optimize=optimize)
