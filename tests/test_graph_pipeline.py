from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")

import gantt_project.build_graph_config as graph_builder  # noqa: E402
import gantt_project.gantt as gantt  # noqa: E402


def _write_config(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


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
    assert tasks == [{"Task": "instant", "Start": 0, "Duration": 0, "Progress": 100.0}]


def test_gantt_render_chart_handles_zero_and_empty_tasks(monkeypatch: object) -> None:
    monkeypatch.setattr(gantt.plt, "show", lambda: None)
    gantt.render_chart("zero", [{"Task": "instant", "Start": 0, "Duration": 0}])
    gantt.render_chart("empty", [])


def test_gantt_figure_height_is_capped() -> None:
    assert gantt._figure_height(1) == 3.0
    assert gantt._figure_height(10_000) == gantt.MAX_FIGURE_HEIGHT


def test_gantt_render_uses_unique_task_lanes(monkeypatch: object) -> None:
    seen: dict[str, int] = {}

    def fake_height(task_count: int) -> float:
        seen["task_count"] = task_count
        return 3.0

    monkeypatch.setattr(gantt, "_figure_height", fake_height)
    monkeypatch.setattr(gantt.plt, "show", lambda: None)
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


def test_gantt_render_repeated_task_uses_same_color(monkeypatch: object) -> None:
    monkeypatch.setattr(gantt.plt, "show", lambda: None)
    gantt.render_chart(
        "repeated",
        [
            {"Task": "repeat", "Start": 0, "Duration": 3},
            {"Task": "repeat", "Start": 1, "Duration": 3},
            {"Task": "repeat", "Start": 2, "Duration": 3},
        ],
    )

    ax = gantt.plt.gca()
    colors = {patch.get_facecolor() for patch in ax.patches}
    assert len(colors) == 1


def test_gantt_window_title_from_chart_title() -> None:
    assert gantt._window_title("Diagramme de Gantt - ikea") == "Graph_gantt_ikea"


def test_gantt_render_uses_uniform_height_and_spacing(monkeypatch: object) -> None:
    monkeypatch.setattr(gantt.plt, "show", lambda: None)
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

    ax = gantt.plt.gca()
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
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(gantt.plt, "show", lambda: None)
    gantt.render_chart(
        "progress",
        [
            {"Task": "long", "Start": 0, "Duration": 20, "Progress": 75},
            {"Task": "short", "Start": 0, "Duration": 0, "Progress": 50},
        ],
    )

    labels = {text.get_text() for text in gantt.plt.gca().texts}
    assert "75%" in labels
    assert "50%" not in labels


def test_gantt_render_balances_outer_horizontal_spaces(monkeypatch: object) -> None:
    monkeypatch.setattr(gantt.plt, "show", lambda: None)
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

    fig = gantt.plt.gcf()
    ax = gantt.plt.gca()
    left_space, right_space = gantt._outer_spaces(fig, ax)
    assert left_space == pytest.approx(right_space, abs=0.01)


def test_gantt_render_uses_same_gap_between_adjacent_task_groups(
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(gantt.plt, "show", lambda: None)
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
        patch.get_y() + patch.get_height() / 2.0
        for patch in gantt.plt.gca().patches
    ]
    e0, e1, e2, m0, m1, f0, a0 = centers
    gap_em = m0 - e2
    gap_mf = f0 - m1
    gap_fa = a0 - f0
    assert gap_em == pytest.approx(gap_mf)
    assert gap_em == pytest.approx(gap_fa)
