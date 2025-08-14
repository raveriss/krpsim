from pathlib import Path

from krpsim.display import format_trace, save_trace


def test_format_trace() -> None:
    trace = [(0, "p1"), (10, "p2")]
    assert format_trace(trace) == ["0:p1", "10:p2"]


def test_save_trace(tmp_path: Path) -> None:
    trace = [(0, "p1"), (5, "p2")]
    target = tmp_path / "trace.txt"
    save_trace(trace, target)
    assert target.read_text().splitlines() == ["0:p1", "5:p2"]


def test_save_empty_trace(tmp_path: Path) -> None:
    target = tmp_path / "trace.txt"
    save_trace([], target)
    assert target.read_text().splitlines() == ["# no process executed (optimization)"]
