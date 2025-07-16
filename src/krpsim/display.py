"""Display utilities producing human messages and machine trace."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterable

from .parser import Config


def print_header(config: Config) -> None:
    """Print introduction lines about the config."""
    optimize_count = len(config.optimize or [])
    print(
        "Nice file! "
        f"{len(config.processes)} processes, {len(config.stocks)} stocks, "
        f"{optimize_count} to optimize"
    )
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

