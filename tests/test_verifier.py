from pathlib import Path

import pytest

from krpsim import parser
from krpsim.simulator import Simulator
from krpsim.verifier import TraceError, parse_trace, verify_trace


def test_verify_trace_valid(tmp_path: Path) -> None:
    cfg = parser.parse_file(Path("resources/simple"))
    sim = Simulator(cfg)
    events = sim.run(100)
    trace_file = tmp_path / "trace.txt"
    trace_file.write_text("\n".join(f"{c}:{n}" for c, n in events))
    trace = parse_trace(trace_file)
    verify_trace(cfg, trace)


def test_verify_trace_error(tmp_path: Path) -> None:
    cfg = parser.parse_file(Path("resources/simple"))
    bad_trace = tmp_path / "bad.txt"
    bad_trace.write_text("0:oops\n")
    trace = parse_trace(bad_trace)
    with pytest.raises(TraceError):
        verify_trace(cfg, trace)


@pytest.mark.parametrize(
    "content",
    ["", "0proc", "x:proc"],
)
def test_parse_trace_errors(tmp_path: Path, content: str) -> None:
    file = tmp_path / "trace.txt"
    file.write_text(content + "\n")
    with pytest.raises(TraceError):
        parse_trace(file)


def test_verify_trace_short_and_extra(tmp_path: Path) -> None:
    cfg = parser.parse_file(Path("resources/simple"))
    sim = Simulator(cfg)
    events = sim.run(100)

    short_file = tmp_path / "short.txt"
    short_file.write_text("\n".join(f"{c}:{n}" for c, n in events[:-1]))
    with pytest.raises(TraceError):
        verify_trace(cfg, parse_trace(short_file))

    extra_file = tmp_path / "extra.txt"
    extra_events = events + [(999, "extra")]
    extra_file.write_text("\n".join(f"{c}:{n}" for c, n in extra_events))
    with pytest.raises(TraceError):
        verify_trace(cfg, parse_trace(extra_file))
