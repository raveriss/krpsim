"""Render a Gantt chart from a generated graph JSON configuration."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import MultipleLocator

ZERO_DURATION_WIDTH = 0.4
MAX_FIGURE_HEIGHT = 24.0
MAJOR_TICK_STEP = 10
MINOR_TICK_STEP = 1
TASK_LANE_SPAN = 0.82
PHI = 1.618
TRACK_GAP_RATIO = 0.12
PROGRESS_FONT_SIZE = 8.5
PROGRESS_PADDING_PX = 4.0

TaskField = int | float | str
TaskPayload = dict[str, TaskField]
RgbaColor = tuple[float, float, float, float]


@dataclass
class _TaskBar:
    """Internal representation of a rendered task bar."""

    task: str
    start: int
    duration: int
    display_duration: float
    end: float
    progress: float
    track_index: int = 0
    track_count: int = 1


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for the Gantt renderer."""
    parser = argparse.ArgumentParser(prog="gantt")
    parser.add_argument(
        "--config",
        default="graph_config_simple.json",
        help="path to the graph configuration json file",
    )
    return parser


def load_config(path: Path) -> tuple[str, list[TaskPayload]]:
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

    normalized: list[TaskPayload] = []
    for index, item in enumerate(tasks, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"task #{index} must be a JSON object")
        name = item.get("Task")
        start = item.get("Start")
        duration = item.get("Duration")
        progress = item.get("Progress", 100)
        if not isinstance(name, str) or not name:
            raise ValueError(f"task #{index} has invalid 'Task' value")
        if not isinstance(start, int) or start < 0:
            raise ValueError(f"task #{index} has invalid 'Start' value")
        if not isinstance(duration, int) or duration < 0:
            raise ValueError(f"task #{index} has invalid 'Duration' value")
        if not isinstance(progress, (int, float)) or not (0 <= float(progress) <= 100):
            raise ValueError(f"task #{index} has invalid 'Progress' value")
        normalized.append(
            {
                "Task": name,
                "Start": start,
                "Duration": duration,
                "Progress": float(progress),
            }
        )

    return title, normalized


def _display_duration(duration: int) -> float:
    """Return a visible width for a task duration."""
    if duration > 0:
        return float(duration)
    return ZERO_DURATION_WIDTH


def _figure_height(task_count: int) -> float:
    """Compute a bounded figure height."""
    raw_height = max(3.0, task_count * 0.6 + 1.5)
    return min(MAX_FIGURE_HEIGHT, raw_height)


def _collect_task_order(tasks_data: list[TaskPayload]) -> list[str]:
    """Return task names in their first appearance order."""
    return list(dict.fromkeys(str(task["Task"]) for task in tasks_data))


def _build_bars(tasks_data: list[TaskPayload]) -> list[_TaskBar]:
    """Convert payload tasks into normalized bars."""
    bars: list[_TaskBar] = []
    for task_data in tasks_data:
        task = str(task_data["Task"])
        start = int(task_data["Start"])
        duration = int(task_data["Duration"])
        progress = float(task_data.get("Progress", 100))
        display_duration = _display_duration(duration)
        bars.append(
            _TaskBar(
                task=task,
                start=start,
                duration=duration,
                display_duration=display_duration,
                end=start + display_duration,
                progress=progress,
            )
        )
    return bars


def _assign_tracks(bars: list[_TaskBar]) -> None:
    """Assign sub-tracks per task to separate overlapping repetitions."""
    grouped_indices: dict[str, list[int]] = defaultdict(list)
    for index, bar in enumerate(bars):
        grouped_indices[bar.task].append(index)

    for indices in grouped_indices.values():
        lane_ends: list[float] = []
        for bar_index in sorted(indices, key=lambda idx: (bars[idx].start, idx)):
            bar = bars[bar_index]
            for track_index, lane_end in enumerate(lane_ends):
                if bar.start >= lane_end:
                    bar.track_index = track_index
                    lane_ends[track_index] = bar.end
                    break
            else:
                bar.track_index = len(lane_ends)
                lane_ends.append(bar.end)

        track_count = max(1, len(lane_ends))
        for bar_index in indices:
            bars[bar_index].track_count = track_count


def _color_map(task_order: list[str]) -> dict[str, RgbaColor]:
    """Build a stable color map with one color per distinct task."""
    cmap = plt.get_cmap("tab20")
    palette = [cmap(idx) for idx in range(cmap.N)]
    return {
        task: to_rgba(palette[index % len(palette)])
        for index, task in enumerate(task_order)
    }


def _edge_color(color: RgbaColor) -> RgbaColor:
    """Return a slightly darker stroke color for a bar edge."""
    r, g, b, a = color
    darken = 0.65
    return (r * darken, g * darken, b * darken, a)


def _font_height_in_data_units() -> float:
    """Estimate Y-axis label font height in data units."""
    fig = plt.gcf()
    ax = plt.gca()
    fig.canvas.draw()

    labels = ax.get_yticklabels()
    if labels:
        font_size_pt = float(labels[0].get_fontsize())
    else:
        base = plt.rcParams.get("ytick.labelsize", plt.rcParams.get("font.size", 10.0))
        if isinstance(base, str):
            font_size_pt = float(plt.rcParams.get("font.size", 10.0))
        else:
            font_size_pt = float(base)

    font_height_px = font_size_pt * fig.dpi / 72.0
    y_min, y_max = ax.get_ylim()
    data_per_px = abs(y_max - y_min) / max(ax.bbox.height, 1.0)
    return font_height_px * data_per_px


def _x_data_per_pixel(ax: plt.Axes) -> float:
    """Return horizontal data units represented by one display pixel."""
    x_min, x_max = ax.get_xlim()
    return abs(x_max - x_min) / max(ax.bbox.width, 1.0)


def _text_width_in_data_units(ax: plt.Axes, text: str, font_size: float) -> float:
    """Measure text width in X-axis data units."""
    renderer = ax.figure.canvas.get_renderer()
    probe = ax.text(0.0, 0.0, text, fontsize=font_size, alpha=0.0)
    bbox = probe.get_window_extent(renderer=renderer)
    probe.remove()
    return bbox.width * _x_data_per_pixel(ax)


def _progress_label(progress: float) -> str:
    """Format a progress value as compact percentage text."""
    if progress.is_integer():
        return f"{int(progress)}%"
    return f"{progress:.1f}%"


def _label_color(fill_color: RgbaColor) -> str:
    """Choose a readable text color on top of a bar fill color."""
    red, green, blue, _ = fill_color
    luma = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    return "#111111" if luma >= 0.6 else "#ffffff"


def _window_title(chart_title: str) -> str:
    """Build the native window title from chart title."""
    _, _, tail = chart_title.partition("-")
    dataset_name = tail.strip() if tail.strip() else chart_title.strip()
    compact_name = "_".join(part for part in dataset_name.split() if part)
    return f"Graph_gantt_{compact_name}"


def _set_window_title(fig: plt.Figure, chart_title: str) -> None:
    """Apply window title when the backend manager supports it."""
    manager = getattr(fig.canvas, "manager", None)
    if manager is None:
        return
    setter = getattr(manager, "set_window_title", None)
    if callable(setter):
        setter(_window_title(chart_title))


def _outer_spaces(fig: plt.Figure, ax: plt.Axes) -> tuple[float, float]:
    """Return current left/right outer spaces in figure fraction."""
    renderer = fig.canvas.get_renderer()
    tight_box = ax.get_tightbbox(renderer).transformed(fig.transFigure.inverted())
    left_space = tight_box.x0
    right_space = 1.0 - tight_box.x1
    return left_space, right_space


def _balance_horizontal_whitespace(fig: plt.Figure, ax: plt.Axes) -> None:
    """Center chart content by balancing outer left/right spaces."""
    fig.canvas.draw()
    left_space, right_space = _outer_spaces(fig, ax)
    delta = left_space - right_space
    if abs(delta) <= 1e-3:
        return

    position = ax.get_position()
    min_width = 0.2
    shrink = min(abs(delta), max(0.0, position.width - min_width))
    if shrink <= 0.0:
        return

    if delta > 0.0:
        # Left is wider: keep left anchor, reduce width from right side.
        new_position = [
            position.x0,
            position.y0,
            position.width - shrink,
            position.height,
        ]
    else:
        # Right is wider: shift axis right and reduce width from left side.
        new_position = [
            position.x0 + shrink,
            position.y0,
            position.width - shrink,
            position.height,
        ]
    ax.set_position(new_position)
    fig.canvas.draw()


def _draw_rounded_bar(
    *,
    ax: plt.Axes,
    start: float,
    width: float,
    center_y: float,
    height: float,
    color: RgbaColor,
) -> None:
    """Draw one rounded horizontal bar."""
    # Oblong capsule style: maximal corner radius within bar dimensions.
    rounding = max(0.02, min(height, width / 2.0))
    patch = FancyBboxPatch(
        (start, center_y - height / 2.0),
        width,
        height,
        boxstyle=f"round,pad=0,rounding_size={rounding}",
        linewidth=0.9,
        edgecolor=_edge_color(color),
        facecolor=color,
    )
    ax.add_patch(patch)


def render_chart(title: str, tasks_data: list[TaskPayload]) -> None:
    """Render the chart from validated task data."""
    task_order = _collect_task_order(tasks_data)
    lanes = len(task_order)
    height = _figure_height(lanes)
    fig, ax = plt.subplots(figsize=(10, height))
    _set_window_title(fig, title)

    if not tasks_data:
        ax.set_xlabel("Temps")
        ax.set_ylabel("Taches")
        ax.set_title(title)
        ax.text(
            0.5,
            0.5,
            "Aucune tache a afficher",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.xaxis.set_major_locator(MultipleLocator(MAJOR_TICK_STEP))
        ax.xaxis.set_minor_locator(MultipleLocator(MINOR_TICK_STEP))
        ax.grid(True, axis="x", which="major", linestyle="-", linewidth=0.9, alpha=0.45)
        ax.grid(True, axis="x", which="minor", linestyle="-", linewidth=0.5, alpha=0.22)
        fig.tight_layout()
        _balance_horizontal_whitespace(fig, ax)
        plt.show()
        return

    bars = _build_bars(tasks_data)
    _assign_tracks(bars)

    track_count_by_task: dict[str, int] = {}
    for bar in bars:
        track_count_by_task[bar.task] = max(
            track_count_by_task.get(bar.task, 1),
            bar.track_count,
        )

    colors = _color_map(task_order)
    global_track_count = max((bar.track_count for bar in bars), default=1)

    # Keep a compact layout while enforcing the same gap between adjacent tasks.
    track_band = TASK_LANE_SPAN / max(1, global_track_count)
    if len(task_order) >= 2:
        first_count = track_count_by_task[task_order[0]]
        second_count = track_count_by_task[task_order[1]]
        desired_group_gap = 1.0 - ((first_count + second_count - 2) / 2.0) * track_band
    else:
        desired_group_gap = 1.0
    desired_group_gap = max(track_band * 0.35, desired_group_gap)

    task_first_center: dict[str, float] = {}
    task_label_center: dict[str, float] = {}
    for index, task in enumerate(task_order):
        if index == 0:
            first_center = 0.0
        else:
            previous_task = task_order[index - 1]
            prev_count = track_count_by_task[previous_task]
            prev_last_center = (
                task_first_center[previous_task]
                + track_band * (prev_count - 1)
            )
            first_center = prev_last_center + desired_group_gap
        task_first_center[task] = first_center
        task_count = track_count_by_task[task]
        task_label_center[task] = first_center + track_band * (task_count - 1) / 2.0

    max_last_center = max(
        task_first_center[task] + track_band * (track_count_by_task[task] - 1)
        for task in task_order
    )

    max_end = max(bar.end for bar in bars)
    x_margin = max(1.0, max_end * 0.02)
    ax.set_xlim(0, max_end + x_margin)
    ax.set_ylim(-0.5, max_last_center + 0.5)
    ax.set_yticks([task_label_center[task] for task in task_order], labels=task_order)
    ax.set_axisbelow(True)

    # Compute target bar height from label font height * golden ratio.
    target_height = PHI * _font_height_in_data_units()
    track_height_cap = track_band * (1.0 - TRACK_GAP_RATIO)
    bar_height = max(0.05, min(target_height, track_height_cap))
    progress_width_cache: dict[str, float] = {}
    right_padding = PROGRESS_PADDING_PX * _x_data_per_pixel(ax)

    for bar in bars:
        center_y = task_first_center[bar.task] + track_band * bar.track_index

        _draw_rounded_bar(
            ax=ax,
            start=float(bar.start),
            width=bar.display_duration,
            center_y=center_y,
            height=bar_height,
            color=colors[bar.task],
        )

        label = _progress_label(bar.progress)
        if label not in progress_width_cache:
            progress_width_cache[label] = _text_width_in_data_units(
                ax,
                label,
                PROGRESS_FONT_SIZE,
            )
        required = progress_width_cache[label] + right_padding * 2.0
        if bar.display_duration >= required:
            ax.text(
                bar.start + bar.display_duration - right_padding,
                center_y,
                label,
                ha="right",
                va="center",
                fontsize=PROGRESS_FONT_SIZE,
                color=_label_color(colors[bar.task]),
            )

    ax.set_xlabel("Temps")
    ax.set_ylabel("Taches")
    ax.set_title(title)
    ax.xaxis.set_major_locator(MultipleLocator(MAJOR_TICK_STEP))
    ax.xaxis.set_minor_locator(MultipleLocator(MINOR_TICK_STEP))
    ax.grid(True, axis="x", which="major", linestyle="-", linewidth=0.9, alpha=0.45)
    ax.grid(True, axis="x", which="minor", linestyle="-", linewidth=0.5, alpha=0.22)

    fig.tight_layout()
    _balance_horizontal_whitespace(fig, ax)
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
