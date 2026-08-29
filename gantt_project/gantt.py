"""Render a Gantt chart from a generated graph JSON configuration."""

from __future__ import annotations

import argparse
import heapq
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import MultipleLocator

from logger.analysis_log_gantt_project import (
    AnalysisLogger,
    get_active_analysis_logger,
    set_active_analysis_logger,
)

ZERO_DURATION_WIDTH = 0.4
MAX_RENDERED_BARS = 5_000
OUTPUT_DPI = 160
DESKTOP_WIDTH_PX = 1_920
DESKTOP_HEIGHT_PX = 1_080
FIGURE_WIDTH = DESKTOP_WIDTH_PX / OUTPUT_DPI
DESKTOP_FIGURE_HEIGHT = DESKTOP_HEIGHT_PX / OUTPUT_DPI
DESKTOP_LANE_CAPACITY = 15
EXTRA_LANE_HEIGHT = 0.42
MAX_FIGURE_HEIGHT = 24.0
MAJOR_TICK_STEP = 10
MINOR_TICK_STEP = 1
MIN_TIMELINE_SPAN = float(MAJOR_TICK_STEP)
TASK_LANE_SPAN = 0.82
DEFAULT_GRAPH_DIR = Path("docs/graphs")
NON_INTERACTIVE_BACKENDS = {"agg", "cairo", "pdf", "pgf", "ps", "svg", "template"}
PHI = 1.618
TRACK_GAP_RATIO = 0.12
PROGRESS_FONT_SIZE = 8.5
PROGRESS_PADDING_PX = 4.0

TaskField = int | float | str
TaskPayload = dict[str, TaskField]
RgbaColor = tuple[float, float, float, float]


class _RendererCanvas(Protocol):
    def get_renderer(self) -> RendererBase: ...


@dataclass
class _TaskBar:
    """Internal representation of a rendered task bar."""

    task: str
    start: int
    duration: int
    display_duration: float
    end: float
    progress: float
    count: int = 1
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
    parser.add_argument(
        "--analysis-log",
        action="store_true",
        help="print detailed analysis logs for Gantt rendering",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="path where the chart image should be saved",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="do not open an interactive chart window",
    )
    return parser


def load_config(path: Path) -> tuple[str, list[TaskPayload]]:
    """Load and validate graph configuration file."""
    analysis_logger = get_active_analysis_logger()
    scope = "gantt.load_config"
    analysis_logger.log_header("GRAPH CONFIG LOAD", scope=scope)
    analysis_logger.log_key_value("CONFIG_PATH", str(path), scope=scope)
    if not path.is_file():
        analysis_logger.log_step("CONFIG_PATH_ERROR", str(path), scope=scope)
        raise FileNotFoundError(f"invalid graph config path: '{path}'")

    raw_text = path.read_text(encoding="utf-8")
    analysis_logger.log_key_value("RAW_JSON", raw_text, scope=scope)
    data = json.loads(raw_text)
    analysis_logger.log_key_value("DECODED_JSON", data, scope=scope)
    if not isinstance(data, dict):
        analysis_logger.log_step("CONFIG_SCHEMA_ERROR", "root_not_object", scope=scope)
        raise ValueError("graph config must be a JSON object")

    title = data.get("title")
    tasks = data.get("tasks")
    analysis_logger.log_key_value(
        "TOP_LEVEL_FIELDS",
        {"title": title, "tasks_type": type(tasks).__name__},
        scope=scope,
    )

    if not isinstance(title, str) or not title.strip():
        analysis_logger.log_step("CONFIG_SCHEMA_ERROR", "invalid_title", scope=scope)
        raise ValueError("graph config must define a non-empty 'title'")
    if not isinstance(tasks, list):
        analysis_logger.log_step("CONFIG_SCHEMA_ERROR", "invalid_tasks", scope=scope)
        raise ValueError("graph config must define a 'tasks' list")

    normalized: list[TaskPayload] = []
    for index, item in enumerate(tasks, start=1):
        analysis_logger.log_key_value(
            "TASK_READ",
            {"index": index, "payload": item},
            scope=scope,
        )
        if not isinstance(item, dict):
            analysis_logger.log_step(
                "TASK_SCHEMA_ERROR",
                {"index": index, "reason": "not_object"},
                scope=scope,
            )
            raise ValueError(f"task #{index} must be a JSON object")
        name = item.get("Task")
        start = item.get("Start")
        duration = item.get("Duration")
        progress = item.get("Progress", 100)
        count = item.get("Count", 1)
        if not isinstance(name, str) or not name:
            analysis_logger.log_step(
                "TASK_SCHEMA_ERROR",
                {"index": index, "field": "Task", "value": name},
                scope=scope,
            )
            raise ValueError(f"task #{index} has invalid 'Task' value")
        if not isinstance(start, int) or start < 0:
            analysis_logger.log_step(
                "TASK_SCHEMA_ERROR",
                {"index": index, "field": "Start", "value": start},
                scope=scope,
            )
            raise ValueError(f"task #{index} has invalid 'Start' value")
        if not isinstance(duration, int) or duration < 0:
            analysis_logger.log_step(
                "TASK_SCHEMA_ERROR",
                {"index": index, "field": "Duration", "value": duration},
                scope=scope,
            )
            raise ValueError(f"task #{index} has invalid 'Duration' value")
        if not isinstance(progress, (int, float)) or not (0 <= float(progress) <= 100):
            analysis_logger.log_step(
                "TASK_SCHEMA_ERROR",
                {"index": index, "field": "Progress", "value": progress},
                scope=scope,
            )
            raise ValueError(f"task #{index} has invalid 'Progress' value")
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
            analysis_logger.log_step(
                "TASK_SCHEMA_ERROR",
                {"index": index, "field": "Count", "value": count},
                scope=scope,
            )
            raise ValueError(f"task #{index} has invalid 'Count' value")
        normalized_task: TaskPayload = {
            "Task": name,
            "Start": start,
            "Duration": duration,
            "Progress": float(progress),
            "Count": count,
        }
        analysis_logger.log_key_value(
            "TASK_NORMALIZED",
            normalized_task,
            scope=scope,
        )
        normalized.append(normalized_task)

    analysis_logger.log_key_value("TITLE", title, scope=scope)
    analysis_logger.log_key_value("NORMALIZED_TASKS", normalized, scope=scope)
    return title, normalized


def _display_duration(duration: int) -> float:
    """Return a visible width for a task duration."""
    if duration > 0:
        return float(duration)
    return ZERO_DURATION_WIDTH


def _figure_height(task_count: int) -> float:
    """Compute a 1080p-first height that grows for additional process lanes."""
    extra_lanes = max(0, task_count - DESKTOP_LANE_CAPACITY)
    raw_height = DESKTOP_FIGURE_HEIGHT + extra_lanes * EXTRA_LANE_HEIGHT
    result = min(MAX_FIGURE_HEIGHT, raw_height)
    get_active_analysis_logger().log_calculation(
        "FIGURE_HEIGHT",
        [
            "raw_height = desktop_height + extra_lanes * extra_lane_height",
            f"task_count = {task_count}",
            f"desktop_lane_capacity = {DESKTOP_LANE_CAPACITY}",
            f"max_height = {MAX_FIGURE_HEIGHT}",
        ],
        result,
        scope="gantt._figure_height",
    )
    return result


def _collect_task_order(tasks_data: list[TaskPayload]) -> list[str]:
    """Return task names in their first appearance order."""
    result = list(dict.fromkeys(str(task["Task"]) for task in tasks_data))
    get_active_analysis_logger().log_key_value(
        "TASK_ORDER",
        result,
        scope="gantt._collect_task_order",
    )
    return result


def _compact_tasks(
    tasks_data: list[TaskPayload],
    *,
    max_bars: int = MAX_RENDERED_BARS,
) -> tuple[list[TaskPayload], bool]:
    """Aggregate dense timelines into bounded per-process time buckets."""
    if len(tasks_data) <= max_bars:
        return tasks_data, False

    task_order = _collect_task_order(tasks_data)
    bucket_count = max(1, max_bars // max(1, len(task_order)))
    max_start = max(int(task["Start"]) for task in tasks_data)
    bucket_width = max(1, math.ceil((max_start + 1) / bucket_count))
    groups: dict[tuple[str, int], dict[str, int | float | str | bool]] = {}

    for task in tasks_data:
        name = str(task["Task"])
        start = int(task["Start"])
        duration = int(task["Duration"])
        count = int(task.get("Count", 1))
        progress = float(task.get("Progress", 100))
        bucket = start // bucket_width
        key = (name, bucket)
        group = groups.get(key)
        if group is None:
            groups[key] = {
                "Task": name,
                "Start": start,
                "LastStart": start,
                "End": start + duration,
                "Count": count,
                "ProgressTotal": progress * count,
                "AllInstant": duration == 0,
            }
            continue

        group["Start"] = min(int(group["Start"]), start)
        group["LastStart"] = max(int(group["LastStart"]), start)
        group["End"] = max(int(group["End"]), start + duration)
        group["Count"] = int(group["Count"]) + count
        group["ProgressTotal"] = float(group["ProgressTotal"]) + progress * count
        group["AllInstant"] = bool(group["AllInstant"]) and duration == 0

    compacted: list[TaskPayload] = []
    for group in groups.values():
        start = int(group["Start"])
        last_start = int(group["LastStart"])
        end = int(group["End"])
        count = int(group["Count"])
        all_instant = bool(group["AllInstant"])
        duration = 0 if all_instant and start == last_start else max(1, end - start)
        compacted.append(
            {
                "Task": str(group["Task"]),
                "Start": start,
                "Duration": duration,
                "Progress": float(group["ProgressTotal"]) / count,
                "Count": count,
            }
        )

    get_active_analysis_logger().log_key_value(
        "TIMELINE_COMPACTION",
        {
            "input_groups": len(tasks_data),
            "output_groups": len(compacted),
            "max_bars": max_bars,
            "bucket_width": bucket_width,
        },
        scope="gantt._compact_tasks",
    )
    return compacted, True


def _tick_steps(visible_span: float) -> tuple[float, float]:
    """Return readable major/minor tick steps without creating huge tick lists."""
    rough_step = max(float(MAJOR_TICK_STEP), visible_span / 20.0)
    magnitude = 10.0 ** math.floor(math.log10(rough_step))
    normalized = rough_step / magnitude
    if normalized <= 1.0:
        multiplier = 1.0
    elif normalized <= 2.0:
        multiplier = 2.0
    elif normalized <= 5.0:
        multiplier = 5.0
    else:
        multiplier = 10.0
    major_step = multiplier * magnitude
    minor_step = max(float(MINOR_TICK_STEP), major_step / 5.0)
    return major_step, minor_step


def _configure_time_axis(ax: Axes, visible_span: float) -> None:
    """Configure an adaptive X axis whose cost is independent of cycle count."""
    major_step, minor_step = _tick_steps(visible_span)
    ax.xaxis.set_major_locator(MultipleLocator(major_step))
    ax.xaxis.set_minor_locator(MultipleLocator(minor_step))
    ax.grid(True, axis="x", which="major", linestyle="-", linewidth=0.9, alpha=0.45)
    ax.grid(True, axis="x", which="minor", linestyle="-", linewidth=0.5, alpha=0.22)


def _build_bars(tasks_data: list[TaskPayload]) -> list[_TaskBar]:
    """Convert payload tasks into normalized bars."""
    analysis_logger = get_active_analysis_logger()
    scope = "gantt._build_bars"
    analysis_logger.log_header("TASK BAR BUILD", scope=scope)
    analysis_logger.log_key_value("TASKS_DATA", tasks_data, scope=scope)
    bars: list[_TaskBar] = []
    for task_data in tasks_data:
        task = str(task_data["Task"])
        start = int(task_data["Start"])
        duration = int(task_data["Duration"])
        progress = float(task_data.get("Progress", 100))
        count = int(task_data.get("Count", 1))
        display_duration = _display_duration(duration)
        bars.append(
            _TaskBar(
                task=task,
                start=start,
                duration=duration,
                display_duration=display_duration,
                end=float(start + duration),
                progress=progress,
                count=count,
            )
        )
        analysis_logger.log_key_value(
            "BAR_CREATED",
            bars[-1],
            scope=scope,
        )
    analysis_logger.log_key_value("BARS", bars, scope=scope)
    return bars


def _assign_tracks(bars: list[_TaskBar]) -> None:
    """Assign overlap tracks in O(N log N) time using priority queues."""
    analysis_logger = get_active_analysis_logger()
    scope = "gantt._assign_tracks"
    analysis_logger.log_header("TRACK ASSIGNMENT", scope=scope)
    analysis_logger.log_key_value("INPUT_BARS", bars, scope=scope)
    grouped_indices: dict[str, list[int]] = defaultdict(list)
    for index, bar in enumerate(bars):
        grouped_indices[bar.task].append(index)
    analysis_logger.log_key_value("GROUPED_INDICES", dict(grouped_indices), scope=scope)

    for indices in grouped_indices.values():
        active_tracks: list[tuple[float, int]] = []
        free_tracks: list[int] = []
        track_count = 0
        for bar_index in sorted(indices, key=lambda idx: (bars[idx].start, idx)):
            bar = bars[bar_index]
            while active_tracks and active_tracks[0][0] <= bar.start:
                _, released_track = heapq.heappop(active_tracks)
                heapq.heappush(free_tracks, released_track)

            if free_tracks:
                bar.track_index = heapq.heappop(free_tracks)
                event = "TRACK_REUSED"
            else:
                bar.track_index = track_count
                track_count += 1
                event = "TRACK_CREATED"
            heapq.heappush(active_tracks, (bar.end, bar.track_index))
            analysis_logger.log_key_value(
                event,
                {
                    "bar_index": bar_index,
                    "bar": bar,
                    "track_index": bar.track_index,
                    "active_tracks": active_tracks,
                },
                scope=scope,
            )

        track_count = max(1, track_count)
        for bar_index in indices:
            bars[bar_index].track_count = track_count
    analysis_logger.log_key_value("ASSIGNED_BARS", bars, scope=scope)


def _color_map(task_order: list[str]) -> dict[str, RgbaColor]:
    """Build a stable color map with one color per distinct task."""
    cmap = cast(Any, mpl).colormaps["tab20"]
    palette = [cmap(idx) for idx in range(cmap.N)]
    colors = {
        task: cast(RgbaColor, to_rgba(cast(Any, palette[index % len(palette)])))
        for index, task in enumerate(task_order)
    }
    get_active_analysis_logger().log_key_value(
        "COLOR_MAP",
        colors,
        scope="gantt._color_map",
    )
    return colors


def _edge_color(color: RgbaColor) -> RgbaColor:
    """Return a slightly darker stroke color for a bar edge."""
    r, g, b, a = color
    darken = 0.65
    return (r * darken, g * darken, b * darken, a)


def _font_height_in_data_units() -> float:
    """Estimate Y-axis label font height in data units."""
    fig = plt.gcf()
    ax = fig.gca()
    fig.canvas.draw()

    labels = cast(Any, ax).get_yticklabels()
    if labels:
        font_size_pt = float(labels[0].get_fontsize())
    else:
        base = plt.rcParams.get("ytick.labelsize", plt.rcParams.get("font.size", 10.0))
        if isinstance(base, str):
            font_size_pt = float(plt.rcParams.get("font.size", 10.0))
        else:
            font_size_pt = float(base)

    font_height_px = font_size_pt * fig.get_dpi() / 72.0
    y_min, y_max = ax.get_ylim()
    data_per_px = abs(y_max - y_min) / max(ax.get_window_extent().height, 1.0)
    return font_height_px * data_per_px


def _x_data_per_pixel(ax: Axes) -> float:
    """Return horizontal data units represented by one display pixel."""
    x_min, x_max = ax.get_xlim()
    return abs(x_max - x_min) / max(ax.get_window_extent().width, 1.0)


def _text_width_in_data_units(ax: Axes, text: str, font_size: float) -> float:
    """Measure text width in X-axis data units."""
    renderer = cast(_RendererCanvas, ax.figure.canvas).get_renderer()
    probe = ax.text(0.0, 0.0, text, fontsize=font_size, alpha=0.0)
    bbox = probe.get_window_extent(renderer=renderer)
    probe.remove()
    return float(bbox.width) * _x_data_per_pixel(ax)


def _progress_label(progress: float) -> str:
    """Format a progress value as compact percentage text."""
    if progress.is_integer():
        return f"{int(progress)}%"
    return f"{progress:.1f}%"


def _count_label(count: int) -> str:
    """Format an execution multiplicity for chart annotations."""
    return f"×{count:,}".replace(",", " ")


def _select_multiplicity_indices(
    bars: list[_TaskBar],
    visible_span: float,
) -> set[int]:
    """Select one representative maximum-count label per process."""
    candidates_by_task: dict[str, list[int]] = defaultdict(list)
    for index, bar in enumerate(bars):
        if bar.count > 1:
            candidates_by_task[bar.task].append(index)

    timeline_center = visible_span / 2.0
    selected: set[int] = set()
    for indices in candidates_by_task.values():
        maximum_count = max(bars[index].count for index in indices)
        maximum_indices = [
            index for index in indices if bars[index].count == maximum_count
        ]
        representative = min(
            maximum_indices,
            key=lambda index: (
                abs(
                    bars[index].start
                    + bars[index].display_duration / 2.0
                    - timeline_center
                ),
                index,
            ),
        )
        selected.add(representative)
    return selected


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
    result = f"Graph_gantt_{compact_name}"
    get_active_analysis_logger().log_key_value(
        "WINDOW_TITLE",
        {"chart_title": chart_title, "window_title": result},
        scope="gantt._window_title",
    )
    return result


def _set_window_title(fig: Figure, chart_title: str) -> None:
    """Apply window title when the backend manager supports it."""
    manager = getattr(fig.canvas, "manager", None)
    if manager is None:
        return
    setter = getattr(manager, "set_window_title", None)
    if callable(setter):
        setter(_window_title(chart_title))


def _can_show_plot() -> bool:
    """Return whether the active Matplotlib backend can show GUI windows."""
    backend = mpl.get_backend().lower()
    if backend.startswith("module://matplotlib_inline"):
        return False
    return backend not in NON_INTERACTIVE_BACKENDS


def _default_output_path(config_path: Path) -> Path:
    """Build a deterministic output path for a graph configuration."""
    stem = config_path.stem
    prefix = "graph_config_"
    if stem.startswith(prefix):
        stem = stem[len(prefix) :]
    return DEFAULT_GRAPH_DIR / f"diagramme_gantt_{stem}.png"


def _finish_figure(
    fig: Figure,
    *,
    output_path: Path | None,
    show: bool,
) -> Path | None:
    """Save and/or display the rendered figure according to runtime support."""
    analysis_logger = get_active_analysis_logger()
    scope = "gantt._finish_figure"
    saved_path: Path | None = None

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=OUTPUT_DPI)
        saved_path = output_path
        analysis_logger.log_step("PLOT_SAVE", str(output_path), scope=scope)
        print(f"[GRAPH] Fichier genere: {output_path}")

    if show:
        if _can_show_plot():
            analysis_logger.log_step("PLOT_SHOW", mpl.get_backend(), scope=scope)
            plt.show()
        elif output_path is not None:
            print(
                "[GRAPH] Affichage interactif indisponible "
                f"(backend Matplotlib: {mpl.get_backend()})."
            )

    return saved_path


def _outer_spaces(fig: Figure, ax: Axes) -> tuple[float, float]:
    """Return current left/right outer spaces in figure fraction."""
    renderer = cast(_RendererCanvas, fig.canvas).get_renderer()
    transform = cast(Any, fig).transFigure
    tight_box = ax.get_tightbbox(renderer).transformed(transform.inverted())
    left_space = tight_box.x0
    right_space = 1.0 - tight_box.x1
    return left_space, right_space


def _balance_horizontal_whitespace(fig: Figure, ax: Axes) -> None:
    """Center chart content by balancing outer left/right spaces."""
    analysis_logger = get_active_analysis_logger()
    scope = "gantt._balance_horizontal_whitespace"
    fig.canvas.draw()
    left_space, right_space = _outer_spaces(fig, ax)
    delta = left_space - right_space
    analysis_logger.log_key_value(
        "OUTER_SPACES",
        {"left": left_space, "right": right_space, "delta": delta},
        scope=scope,
    )
    if abs(delta) <= 1e-3:
        analysis_logger.log_step("BALANCE_SKIPPED", "already_balanced", scope=scope)
        return

    position = ax.get_position()
    min_width = 0.2
    shrink = min(abs(delta), max(0.0, position.width - min_width))
    if shrink <= 0.0:
        analysis_logger.log_step("BALANCE_SKIPPED", "no_available_width", scope=scope)
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
    analysis_logger.log_key_value(
        "BALANCED_POSITION",
        new_position,
        scope=scope,
    )


def _draw_rounded_bar(
    *,
    ax: Axes,
    start: float,
    width: float,
    center_y: float,
    height: float,
    color: RgbaColor,
) -> None:
    """Draw one rounded horizontal bar."""
    analysis_logger = get_active_analysis_logger()
    scope = "gantt._draw_rounded_bar"
    # Oblong capsule style: maximal corner radius within bar dimensions.
    rounding = max(0.02, min(height, width / 2.0))
    analysis_logger.log_key_value(
        "DRAW_BAR",
        {
            "start": start,
            "width": width,
            "center_y": center_y,
            "height": height,
            "rounding": rounding,
            "color": color,
        },
        scope=scope,
    )
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


def render_chart(
    title: str,
    tasks_data: list[TaskPayload],
    *,
    output_path: Path | None = None,
    show: bool = True,
) -> Path | None:
    """Render the chart from validated task data."""
    analysis_logger = get_active_analysis_logger()
    scope = "gantt.render_chart"
    analysis_logger.log_header("GANTT RENDER", scope=scope)
    analysis_logger.log_key_value("TITLE", title, scope=scope)
    analysis_logger.log_key_value("TASKS_DATA", tasks_data, scope=scope)
    event_count = sum(int(task.get("Count", 1)) for task in tasks_data)
    source_group_count = len(tasks_data)
    tasks_data, timeline_compacted = _compact_tasks(tasks_data)
    task_order = _collect_task_order(tasks_data)
    lanes = len(task_order)
    height = _figure_height(lanes)
    analysis_logger.log_key_value(
        "FIGURE_INPUTS",
        {"task_order": task_order, "lanes": lanes, "height": height},
        scope=scope,
    )
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH, height))
    _set_window_title(fig, title)

    if not tasks_data:
        analysis_logger.log_step("EMPTY_TASKS_BRANCH", scope=scope)
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
        _configure_time_axis(ax, MIN_TIMELINE_SPAN)
        fig.tight_layout()
        _balance_horizontal_whitespace(fig, ax)
        return _finish_figure(fig, output_path=output_path, show=show)

    bars = _build_bars(tasks_data)
    _assign_tracks(bars)

    track_count_by_task: dict[str, int] = {}
    for bar in bars:
        track_count_by_task[bar.task] = max(
            track_count_by_task.get(bar.task, 1),
            bar.track_count,
        )
    analysis_logger.log_key_value(
        "TRACK_COUNT_BY_TASK",
        track_count_by_task,
        scope=scope,
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
    analysis_logger.log_key_value(
        "TRACK_LAYOUT",
        {
            "global_track_count": global_track_count,
            "track_band": track_band,
            "desired_group_gap": desired_group_gap,
        },
        scope=scope,
    )

    task_first_center: dict[str, float] = {}
    task_label_center: dict[str, float] = {}
    for index, task in enumerate(task_order):
        if index == 0:
            first_center = 0.0
        else:
            previous_task = task_order[index - 1]
            prev_count = track_count_by_task[previous_task]
            prev_last_center = task_first_center[previous_task] + track_band * (
                prev_count - 1
            )
            first_center = prev_last_center + desired_group_gap
        task_first_center[task] = first_center
        task_count = track_count_by_task[task]
        task_label_center[task] = first_center + track_band * (task_count - 1) / 2.0
    analysis_logger.log_key_value(
        "TASK_CENTERS",
        {
            "task_first_center": task_first_center,
            "task_label_center": task_label_center,
        },
        scope=scope,
    )

    max_last_center = max(
        task_first_center[task] + track_band * (track_count_by_task[task] - 1)
        for task in task_order
    )

    max_end = max(bar.end if bar.duration > 0 else float(bar.start) for bar in bars)
    visible_span = max(max_end, MIN_TIMELINE_SPAN)
    x_margin = max(1.0, visible_span * 0.02)
    ax.set_xlim(0, visible_span + x_margin)
    ax.set_ylim(-0.5, max_last_center + 0.5)
    cast(Any, ax).set_yticks([task_label_center[task] for task in task_order])
    cast(Any, ax).set_yticklabels(task_order)
    ax.set_axisbelow(True)
    analysis_logger.log_key_value(
        "AXIS_BOUNDS",
        {
            "max_last_center": max_last_center,
            "max_end": max_end,
            "visible_span": visible_span,
            "x_margin": x_margin,
        },
        scope=scope,
    )

    # Compute target bar height from label font height * golden ratio.
    target_height = PHI * _font_height_in_data_units()
    track_height_cap = track_band * (1.0 - TRACK_GAP_RATIO)
    bar_height = max(0.05, min(target_height, track_height_cap))
    progress_width_cache: dict[str, float] = {}
    right_padding = PROGRESS_PADDING_PX * _x_data_per_pixel(ax)
    analysis_logger.log_key_value(
        "BAR_LAYOUT",
        {
            "target_height": target_height,
            "track_height_cap": track_height_cap,
            "bar_height": bar_height,
            "right_padding": right_padding,
        },
        scope=scope,
    )

    multiplicity_indices = _select_multiplicity_indices(bars, visible_span)
    instant_x: list[float] = []
    instant_y: list[float] = []
    instant_colors: list[RgbaColor] = []
    instant_edges: list[RgbaColor] = []

    for bar_index, bar in enumerate(bars):
        center_y = task_first_center[bar.task] + track_band * bar.track_index
        analysis_logger.log_key_value(
            "BAR_RENDER_START",
            {"bar": bar, "center_y": center_y},
            scope=scope,
        )

        if bar.duration == 0:
            instant_x.append(float(bar.start))
            instant_y.append(center_y)
            instant_colors.append(colors[bar.task])
            instant_edges.append(_edge_color(colors[bar.task]))
        else:
            _draw_rounded_bar(
                ax=ax,
                start=float(bar.start),
                width=bar.display_duration,
                center_y=center_y,
                height=bar_height,
                color=colors[bar.task],
            )

        if bar_index in multiplicity_indices:
            place_on_left = bar.start + bar.display_duration / 2.0 > visible_span * 0.85
            ax.annotate(
                _count_label(bar.count),
                (bar.start + (bar.display_duration / 2.0), center_y),
                xytext=(-3 if place_on_left else 3, 4),
                textcoords="offset points",
                ha="right" if place_on_left else "left",
                va="bottom",
                fontsize=7.5,
                color="#222222",
            )

        label = _progress_label(bar.progress)
        if label not in progress_width_cache:
            progress_width_cache[label] = _text_width_in_data_units(
                ax,
                label,
                PROGRESS_FONT_SIZE,
            )
        required = progress_width_cache[label] + right_padding * 2.0
        label_fits = (
            bar.count == 1 and bar.duration > 0 and bar.display_duration >= required
        )
        analysis_logger.log_key_value(
            "PROGRESS_LABEL_DECISION",
            {
                "bar": bar,
                "label": label,
                "required_width": required,
                "display_duration": bar.display_duration,
                "label_fits": label_fits,
            },
            scope=scope,
        )
        if label_fits:
            ax.text(
                bar.start + bar.display_duration - right_padding,
                center_y,
                label,
                ha="right",
                va="center",
                fontsize=PROGRESS_FONT_SIZE,
                color=_label_color(colors[bar.task]),
            )

    if instant_x:
        cast(Any, ax).scatter(
            instant_x,
            instant_y,
            marker="D",
            s=28,
            c=instant_colors,
            edgecolors=instant_edges,
            linewidths=0.8,
            zorder=3,
        )

    ax.set_xlabel("Temps")
    ax.set_ylabel("Taches")
    title_details: list[str] = []
    if event_count != source_group_count:
        title_details.append(
            f"{event_count:,} exécutions regroupées en {source_group_count:,} groupes"
        )
    if timeline_compacted:
        title_details.append(f"vue agrégée : {len(bars):,} éléments affichés")
    rendered_title = title
    if title_details:
        rendered_title += "\n" + " — ".join(title_details).replace(",", " ")
    ax.set_title(rendered_title)
    _configure_time_axis(ax, visible_span)

    fig.tight_layout()
    _balance_horizontal_whitespace(fig, ax)
    return _finish_figure(fig, output_path=output_path, show=show)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)
    analysis_logger = AnalysisLogger(enabled=args.analysis_log)
    set_active_analysis_logger(analysis_logger)
    scope = "gantt.main"
    analysis_logger.log_header("CLI ENTRYPOINT", scope=scope)
    analysis_logger.log_key_value("PARSED_ARGS", vars(args), scope=scope)

    config_path = Path(args.config)
    output_path = Path(args.output) if args.output else None
    show = not args.no_show
    if output_path is None and show and not _can_show_plot():
        output_path = _default_output_path(config_path)

    title, tasks = load_config(config_path)
    analysis_logger.log_step(
        "RENDER_START",
        {"title": title, "tasks": len(tasks)},
        scope=scope,
    )
    render_chart(title, tasks, output_path=output_path, show=show)
    analysis_logger.log_key_value("EXIT_CODE", 0, scope=scope)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
