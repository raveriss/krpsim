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
