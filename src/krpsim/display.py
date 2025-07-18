"""Display utilities producing human messages and machine trace."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterable

from .parser import Config


_IRREGULAR_PLURALS: dict[str, str] = {"process": "processes"}


def _pluralize(word: str, count: int) -> str:
    """Return ``word`` in singular or plural form depending on ``count``."""
    if count == 1:
        return word
    return _IRREGULAR_PLURALS.get(word, word + "s")


def print_header(config: Config) -> None:
    """Print introduction lines about the config."""
    optimize_count = len(config.optimize or [])
    process_info = (
        f"{len(config.processes)} {_pluralize('process', len(config.processes))}"
    )
    stock_info = f"{len(config.stocks)} {_pluralize('stock', len(config.stocks))}"
    objective_info = f"{optimize_count} {_pluralize('objective', optimize_count)}"
    print("Nice file! " f"{process_info}, {stock_info}, {objective_info}")
    print("Evaluating ... done.")
    print("Main walk")


def format_trace(trace: Iterable[tuple[int, str]]) -> list[str]:
    """Return a list of ``cycle:process`` lines."""
    return [f"{cycle}:{name}" for cycle, name in trace]


def save_trace(trace: Iterable[tuple[int, str]], path: Path) -> None:
    """Save ``trace`` to ``path`` and flush to disk."""
    lines = format_trace(trace)
    with path.open("w", encoding="utf-8") as fh:
        for line in lines:
            fh.write(line + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    logging.getLogger(__name__).info("trace saved to %s", path)
