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
    wrong = [
        TraceEntry(0, "achat_materiel"),
        TraceEntry(0, "achat_materiel"),
    ]
    with pytest.raises(TraceError):
        verify_trace(cfg, wrong)


def test_verify_trace_accepts_alternative_start_cycle() -> None:
    cfg = parser.parse_file(Path("resources/simple"))
    sim = verify_trace(cfg, [TraceEntry(1, "achat_materiel")])

    assert sim.stocks["materiel"] == 1
    assert sim.time == 11


def test_verify_trace_accepts_repeated_process_in_same_cycle() -> None:
    cfg = parser.Config(
        stocks={"raw": 2},
        processes={"make": parser.Process("make", {"raw": 1}, {"done": 1}, 0)},
    )
    sim = verify_trace(cfg, [TraceEntry(0, "make"), TraceEntry(0, "make")])

    assert sim.stocks == {"raw": 0, "done": 2}


def test_verify_trace_empty(cfg_path: Path = Path("resources/simple")) -> None:
    cfg = parser.parse_file(cfg_path)
    verify_trace(cfg, [])


def test_verify_empty_trace_valid(tmp_path: Path) -> None:
    cfg_file = tmp_path / "cfg.txt"
    cfg_file.write_text("a:0\nproc:(a:1):(a:1):1\n")
    cfg = parser.parse_file(cfg_file)
    trace_file = tmp_path / "trace.txt"
    trace_file.write_text("")
    trace = parse_trace(trace_file)
    verify_trace(cfg, trace)


def test_parse_trace_comment(tmp_path: Path) -> None:
    file = tmp_path / "trace.txt"
    file.write_text("# comment\n")
    assert parse_trace(file) == []


def test_parse_trace_accepts_crlf(tmp_path: Path) -> None:
    file = tmp_path / "trace.txt"
    file.write_bytes(b"0:proc\r\n")

    assert parse_trace(file) == [TraceEntry(0, "proc")]


def test_verify_trace_rejects_decreasing_cycles() -> None:
    cfg = parser.Config(
        stocks={"raw": 2},
        processes={"make": parser.Process("make", {"raw": 1}, {"done": 1}, 0)},
    )

    with pytest.raises(TraceError, match="is before"):
        verify_trace(cfg, [TraceEntry(1, "make"), TraceEntry(0, "make")])


def test_verify_empty_trace_with_optimize(tmp_path: Path) -> None:
    cfg_file = tmp_path / "cfg.txt"
    cfg_file.write_text("a:1\nproc:(a:1):(b:1):1\noptimize:(b)\n")
    cfg = parser.parse_file(cfg_file)
    trace_file = tmp_path / "trace.txt"
    trace_file.write_text("# no process executed (optimization)\n")
    trace = parse_trace(trace_file)
    verify_trace(cfg, trace)


def test_verify_trace_empty_no_optimize_error(tmp_path: Path) -> None:
    cfg_file = tmp_path / "cfg.txt"
    cfg_file.write_text("a:1\nproc:(a:1):(b:1):1\n")
    cfg = parser.parse_file(cfg_file)
    with pytest.raises(TraceError):
        verify_trace(cfg, [])


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


def test_verify_finite_resource(tmp_path: Path) -> None:
    cfg = parser.parse_file(Path("resources/finite"))
    sim = Simulator(cfg)
    events = sim.run(10)
    trace_file = tmp_path / "trace.txt"
    trace_file.write_text("\n".join(f"{c}:{n}" for c, n in events))
    verify_trace(cfg, parse_trace(trace_file))


def test_verify_loop_resource(tmp_path: Path) -> None:
    cfg = parser.parse_file(Path("resources/loop"))
    sim = Simulator(cfg)
    events = sim.run(5)
    trace_file = tmp_path / "trace.txt"
    trace_file.write_text("\n".join(f"{c}:{n}" for c, n in events))
    verify_trace(cfg, parse_trace(trace_file))


def test_verify_recre_same_cycle_mixed_delays(tmp_path: Path) -> None:
    cfg = parser.parse_file(Path("resources/recre"))
    sim = Simulator(cfg)
    events = sim.run(120)
    trace_file = tmp_path / "trace.txt"
    trace_file.write_text("\n".join(f"{c}:{n}" for c, n in events))
    verify_trace(cfg, parse_trace(trace_file))
