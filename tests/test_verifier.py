from pathlib import Path

import pytest

from krpsim import parser
from krpsim.simulator import Simulator
from krpsim_verif.verifier import TraceEntry, TraceError, parse_trace, verify_trace


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


def test_verify_trace_mismatch(tmp_path: Path) -> None:
    cfg = parser.parse_file(Path("resources/simple"))
    wrong = [TraceEntry(1, "achat_materiel")]
    with pytest.raises(TraceError):
        verify_trace(cfg, wrong)


def test_verify_trace_empty(cfg_path: Path = Path("resources/simple")) -> None:
    cfg = parser.parse_file(cfg_path)
    with pytest.raises(TraceError):
        verify_trace(cfg, [])


def test_verify_empty_trace_valid(tmp_path: Path) -> None:
    cfg_file = tmp_path / "cfg.txt"
    cfg_file.write_text("a:0\nproc:(a:1):(a:1):1\n")
    cfg = parser.parse_file(cfg_file)
    trace_file = tmp_path / "trace.txt"
    trace_file.write_text("")
    trace = parse_trace(trace_file)
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
    verify_trace(cfg, parse_trace(short_file))

    extra_file = tmp_path / "extra.txt"
    last_proc = events[-1][1]
    extra_events = events + [(999, last_proc)]
    extra_file.write_text("\n".join(f"{c}:{n}" for c, n in extra_events))
    with pytest.raises(TraceError):
        verify_trace(cfg, parse_trace(extra_file))


def test_verify_custom_finite(tmp_path: Path) -> None:
    cfg = parser.parse_file(Path("resources/custom_finite"))
    sim = Simulator(cfg)
    events = sim.run(10)
    trace_file = tmp_path / "trace.txt"
    trace_file.write_text("\n".join(f"{c}:{n}" for c, n in events))
    verify_trace(cfg, parse_trace(trace_file))


def test_verify_custom_infinite(tmp_path: Path) -> None:
    cfg = parser.parse_file(Path("resources/custom_infinite"))
    sim = Simulator(cfg)
    events = sim.run(5)
    trace_file = tmp_path / "trace.txt"
    trace_file.write_text("\n".join(f"{c}:{n}" for c, n in events))
    verify_trace(cfg, parse_trace(trace_file))
