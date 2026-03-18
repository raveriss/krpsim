from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import gantt_project.build_graph_config as graph_builder
import gantt_project.gantt as gantt


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
    assert tasks == [{"Task": "instant", "Start": 0, "Duration": 0}]


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
