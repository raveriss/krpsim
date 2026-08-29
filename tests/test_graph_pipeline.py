from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from PIL import Image  # noqa: E402

import gantt_project.build_graph_config as graph_builder  # noqa: E402
import gantt_project.gantt as gantt  # noqa: E402


def _write_config(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def _current_axes() -> Axes:
    return plt.gcf().axes[-1]


def test_build_graph_config_accepts_comment_trace(tmp_path: Path) -> None:
    config_path = tmp_path / "cfg.txt"
    trace_path = tmp_path / "trace.txt"
    _write_config(
        config_path,
        "\n".join(
            [
                "start:1",
                "finish:(start:1):(done:1):1",
                "optimize:(done)",
            ]
        )
        + "\n",
    )
    trace_path.write_text("# no process executed (optimization)\n", encoding="utf-8")

    payload = graph_builder.build_payload(config_path, trace_path)
    assert payload["tasks"] == []
    assert payload["event_count"] == 0


def test_build_graph_config_aggregates_identical_events(tmp_path: Path) -> None:
    config_path = tmp_path / "cfg.txt"
    trace_path = tmp_path / "trace.txt"
    _write_config(
        config_path,
        "\n".join(
            [
                "start:3",
                "finish:(start:1):(done:1):0",
                "optimize:(done)",
            ]
        )
        + "\n",
    )
    trace_path.write_text("0:finish\n0:finish\n0:finish\n", encoding="utf-8")

    payload = graph_builder.build_payload(config_path, trace_path)

    assert payload["event_count"] == 3
    assert payload["group_count"] == 1
    assert payload["tasks"] == [
        {"Task": "finish", "Start": 0, "Duration": 0, "Count": 3}
    ]


def test_gantt_load_config_accepts_zero_duration(tmp_path: Path) -> None:
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(
        json.dumps(
            {
                "title": "zero-delay",
                "tasks": [{"Task": "instant", "Start": 0, "Duration": 0}],
            }
        ),
        encoding="utf-8",
    )

    title, tasks = gantt.load_config(graph_path)
    assert title == "zero-delay"
    assert tasks == [
        {
            "Task": "instant",
            "Start": 0,
            "Duration": 0,
            "Progress": 100.0,
            "Count": 1,
        }
    ]


def test_gantt_load_config_rejects_invalid_count(tmp_path: Path) -> None:
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(
        json.dumps(
            {
                "title": "bad-count",
                "tasks": [{"Task": "instant", "Start": 0, "Duration": 0, "Count": 0}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid 'Count'"):
        gantt.load_config(graph_path)


def test_gantt_render_chart_handles_zero_and_empty_tasks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "show", lambda: None)
    gantt.render_chart("zero", [{"Task": "instant", "Start": 0, "Duration": 0}])
    gantt.render_chart("empty", [])


def test_gantt_render_chart_writes_output_file(tmp_path: Path) -> None:
    output_path = tmp_path / "chart.png"

    saved_path = gantt.render_chart(
        "saved",
        [{"Task": "instant", "Start": 0, "Duration": 0}],
        output_path=output_path,
        show=False,
    )

    assert saved_path == output_path
    assert output_path.is_file()
    assert output_path.stat().st_size > 0
    with Image.open(output_path) as image:
        assert image.size == (gantt.DESKTOP_WIDTH_PX, gantt.DESKTOP_HEIGHT_PX)


def test_gantt_default_output_path_from_graph_config() -> None:
    assert gantt._default_output_path(Path("graph_config_ikea.json")) == Path(
        "docs/graphs/diagramme_gantt_ikea.png"
    )


def test_gantt_figure_height_is_capped() -> None:
    assert gantt._figure_height(1) == gantt.DESKTOP_FIGURE_HEIGHT
    assert gantt._figure_height(gantt.DESKTOP_LANE_CAPACITY) == (
        gantt.DESKTOP_FIGURE_HEIGHT
    )
    assert gantt._figure_height(gantt.DESKTOP_LANE_CAPACITY + 1) > (
        gantt.DESKTOP_FIGURE_HEIGHT
    )
    assert gantt._figure_height(10_000) == gantt.MAX_FIGURE_HEIGHT


def test_gantt_render_uses_unique_task_lanes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, int] = {}

    def fake_height(task_count: int) -> float:
        seen["task_count"] = task_count
        return 3.0

    monkeypatch.setattr(gantt, "_figure_height", fake_height)
    monkeypatch.setattr(plt, "show", lambda: None)
    gantt.render_chart(
        "dense",
        [{"Task": "rapide", "Start": index, "Duration": 1} for index in range(100)],
    )

    assert seen["task_count"] == 1


def test_gantt_assign_tracks_separates_overlapping_repetitions() -> None:
    bars = gantt._build_bars(
        [
            {"Task": "repeat", "Start": 0, "Duration": 10},
            {"Task": "repeat", "Start": 1, "Duration": 10},
            {"Task": "repeat", "Start": 2, "Duration": 10},
        ]
    )
    gantt._assign_tracks(bars)

    assert [bar.track_index for bar in bars] == [0, 1, 2]
    assert [bar.track_count for bar in bars] == [3, 3, 3]


def test_gantt_assign_tracks_reuses_track_for_instant_events() -> None:
    bars = gantt._build_bars(
        [{"Task": "instant", "Start": index, "Duration": 0} for index in range(20_000)]
    )

    gantt._assign_tracks(bars)

    assert {bar.track_index for bar in bars} == {0}
    assert {bar.track_count for bar in bars} == {1}


def test_gantt_compacts_dense_timeline_and_preserves_event_count() -> None:
    tasks: list[gantt.TaskPayload] = [
        {
            "Task": f"process_{index % 2}",
            "Start": index,
            "Duration": 1,
            "Count": 3,
        }
        for index in range(100)
    ]

    compacted, was_compacted = gantt._compact_tasks(tasks, max_bars=10)

    assert was_compacted is True
    assert len(compacted) <= 10
    assert sum(int(task["Count"]) for task in compacted) == 300


def test_gantt_adapts_ticks_to_long_timeline() -> None:
    major, minor = gantt._tick_steps(50_000)

    assert major >= 2_500
    assert minor >= 500


def test_gantt_render_repeated_task_uses_same_color(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "show", lambda: None)
    gantt.render_chart(
        "repeated",
        [
            {"Task": "repeat", "Start": 0, "Duration": 3},
            {"Task": "repeat", "Start": 1, "Duration": 3},
            {"Task": "repeat", "Start": 2, "Duration": 3},
        ],
    )

    ax = _current_axes()
    colors = {patch.get_facecolor() for patch in ax.patches}
    assert len(colors) == 1


def test_gantt_window_title_from_chart_title() -> None:
    assert gantt._window_title("Diagramme de Gantt - ikea") == "Graph_gantt_ikea"


def test_gantt_render_uses_uniform_height_and_spacing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "show", lambda: None)
    gantt.render_chart(
        "uniform",
        [
            {"Task": "a", "Start": 0, "Duration": 10},
            {"Task": "a", "Start": 1, "Duration": 10},
            {"Task": "a", "Start": 2, "Duration": 10},
            {"Task": "b", "Start": 0, "Duration": 15},
            {"Task": "b", "Start": 1, "Duration": 15},
        ],
    )

    ax = _current_axes()
    patches = ax.patches

    heights = [patch.get_height() for patch in patches]
    assert max(heights) == min(heights)

    centers = [patch.get_y() + patch.get_height() / 2.0 for patch in patches]
    spacing_a_1 = centers[1] - centers[0]
    spacing_a_2 = centers[2] - centers[1]
    spacing_b = centers[4] - centers[3]
    assert spacing_a_1 == pytest.approx(spacing_a_2)
    assert spacing_a_1 == pytest.approx(spacing_b)


def test_gantt_render_shows_progress_label_only_when_it_fits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "show", lambda: None)
    gantt.render_chart(
        "progress",
        [
            {"Task": "long", "Start": 0, "Duration": 20, "Progress": 75},
            {"Task": "short", "Start": 0, "Duration": 0, "Progress": 50},
        ],
    )

    labels = {text.get_text() for text in _current_axes().texts}
    assert "75%" in labels
    assert "50%" not in labels


def test_gantt_render_balances_outer_horizontal_spaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "show", lambda: None)
    gantt.render_chart(
        "Diagramme de Gantt - ikea",
        [
            {"Task": "do_armoire_ikea", "Start": 20, "Duration": 30},
            {"Task": "do_fond", "Start": 0, "Duration": 20},
            {"Task": "do_montant", "Start": 0, "Duration": 15},
            {"Task": "do_montant", "Start": 1, "Duration": 15},
            {"Task": "do_etagere", "Start": 0, "Duration": 10},
            {"Task": "do_etagere", "Start": 1, "Duration": 10},
            {"Task": "do_etagere", "Start": 2, "Duration": 10},
        ],
    )

    fig = plt.gcf()
    ax = _current_axes()
    left_space, right_space = gantt._outer_spaces(fig, ax)
    assert left_space == pytest.approx(right_space, abs=0.01)


def test_gantt_render_uses_same_gap_between_adjacent_task_groups(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "show", lambda: None)
    gantt.render_chart(
        "groups-gap",
        [
            {"Task": "do_etagere", "Start": 0, "Duration": 10},
            {"Task": "do_etagere", "Start": 1, "Duration": 10},
            {"Task": "do_etagere", "Start": 2, "Duration": 10},
            {"Task": "do_montant", "Start": 0, "Duration": 15},
            {"Task": "do_montant", "Start": 1, "Duration": 15},
            {"Task": "do_fond", "Start": 0, "Duration": 20},
            {"Task": "do_armoire_ikea", "Start": 20, "Duration": 30},
        ],
    )

    centers = [
        patch.get_y() + patch.get_height() / 2.0 for patch in _current_axes().patches
    ]
    e0, e1, e2, m0, m1, f0, a0 = centers
    gap_em = m0 - e2
    gap_mf = f0 - m1
    gap_fa = a0 - f0
    assert gap_em == pytest.approx(gap_mf)
    assert gap_em == pytest.approx(gap_fa)


def test_gantt_render_single_instant_task_keeps_timeline_span(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "show", lambda: None)
    gantt.render_chart(
        "instant",
        [{"Task": "do_benef", "Start": 0, "Duration": 0}],
    )

    x_min, x_max = _current_axes().get_xlim()
    assert x_min == 0
    assert x_max >= gantt.MIN_TIMELINE_SPAN


def test_gantt_render_instant_multiplicity_as_one_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "show", lambda: None)
    gantt.render_chart(
        "instant-count",
        [{"Task": "instant", "Start": 5, "Duration": 0, "Count": 1_000_000}],
    )

    ax = _current_axes()
    assert len(ax.patches) == 0
    assert len(ax.collections) == 1
    assert "×1 000 000" in {text.get_text() for text in ax.texts}


def test_gantt_render_shows_one_count_per_process_without_progress_overlap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "show", lambda: None)
    gantt.render_chart(
        "deduplicated-labels",
        [
            {"Task": "repeat", "Start": 0, "Duration": 20, "Count": 10},
            {"Task": "repeat", "Start": 30, "Duration": 20, "Count": 10},
            {"Task": "repeat", "Start": 60, "Duration": 20, "Count": 10},
        ],
    )

    labels = [text.get_text() for text in _current_axes().texts]
    assert labels.count("×10") == 1
    assert "100%" not in labels
