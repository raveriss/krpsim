"""Render a Gantt chart from a generated graph JSON configuration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ZERO_DURATION_WIDTH = 0.4


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for the Gantt renderer."""
    parser = argparse.ArgumentParser(prog="gantt")
    parser.add_argument(
        "--config",
        default="graph_config_simple.json",
        help="path to the graph configuration json file",
    )
    return parser


def load_config(path: Path) -> tuple[str, list[dict[str, int | str]]]:
    """Load and validate graph configuration file."""
    if not path.is_file():
        raise FileNotFoundError(f"invalid graph config path: '{path}'")

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("graph config must be a JSON object")

    title = data.get("title")
    tasks = data.get("tasks")

    if not isinstance(title, str) or not title.strip():
        raise ValueError("graph config must define a non-empty 'title'")
    if not isinstance(tasks, list):
        raise ValueError("graph config must define a 'tasks' list")

    normalized: list[dict[str, int | str]] = []
    for index, item in enumerate(tasks, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"task #{index} must be a JSON object")
        name = item.get("Task")
        start = item.get("Start")
        duration = item.get("Duration")
        if not isinstance(name, str) or not name:
            raise ValueError(f"task #{index} has invalid 'Task' value")
        if not isinstance(start, int) or start < 0:
            raise ValueError(f"task #{index} has invalid 'Start' value")
        if not isinstance(duration, int) or duration < 0:
            raise ValueError(f"task #{index} has invalid 'Duration' value")
        normalized.append({"Task": name, "Start": start, "Duration": duration})

    return title, normalized


def _display_duration(duration: int) -> float:
    """Return a visible width for a task duration."""
    if duration > 0:
        return float(duration)
    return ZERO_DURATION_WIDTH


def render_chart(title: str, tasks_data: list[dict[str, int | str]]) -> None:
    """Render the chart from validated task data."""
    height = max(3.0, len(tasks_data) * 0.6 + 1.5)
    fig, ax = plt.subplots(figsize=(10, height))
    if not tasks_data:
        ax.set_xlabel("Temps")
        ax.set_ylabel("Taches")
        ax.set_title(title)
        ax.text(0.5, 0.5, "Aucune tache a afficher", ha="center", va="center", transform=ax.transAxes)
        ax.grid(True, axis="x", linestyle="--", alpha=0.6)
        plt.tight_layout()
        plt.show()
        return

    df = pd.DataFrame(tasks_data)
    df["DisplayDuration"] = df["Duration"].map(_display_duration)
    for _, row in df.iterrows():
        ax.barh(row["Task"], row["DisplayDuration"], left=row["Start"])

    ax.set_xlabel("Temps")
    ax.set_ylabel("Taches")
    ax.set_title(title)
    ax.grid(True, axis="x", linestyle="--", alpha=0.6)

    plt.tight_layout()
    plt.show()


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    title, tasks = load_config(Path(args.config))
    render_chart(title, tasks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
