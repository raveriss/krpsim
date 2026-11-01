import os
from pathlib import Path
from types import ModuleType

import pytest
from pytest import CaptureFixture, MonkeyPatch

from krpsim import cli, parser
from krpsim_verif import cli as verifier_cli
from krpsim_verif.verifier import verify_files


def test_cli_help(capsys: CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["-h"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out.lower()
    assert "inclusive upper bound" in captured.out


def test_cli_invalid_path():
    with pytest.raises(SystemExit) as exc:
        cli.main(["/does/not/exist", "1"])
    assert exc.value.code == 2


def test_cli_invalid_delay(tmp_path: Path) -> None:
    config = tmp_path / "conf.txt"
    config.write_text("dummy")
    with pytest.raises(SystemExit) as exc:
        cli.main([str(config), "0"])
    assert exc.value.code == 2


def test_cli_delay_help_text() -> None:
    parser = cli.build_parser()
    assert "inclusive upper bound" in parser.format_help()


def test_verifier_cli_help(capsys: CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        verifier_cli.main(["-h"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "usage" in captured.out.lower()


def test_verifier_cli_valid(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    cfg = tmp_path / "conf.txt"
    cfg.write_text("a:1\nproc:(a:1):(b:1):1\n")
    trace = tmp_path / "trace.txt"
    trace.write_text("0:proc\n")
    assert verifier_cli.main([str(cfg), str(trace)]) == 0
    captured = capsys.readouterr()
    assert "trace is valid" in captured.out


def test_verifier_cli_error(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    cfg = tmp_path / "conf.txt"
    cfg.write_text("a:1\nproc:(a:1):(b:1):1\n")
    trace = tmp_path / "trace.txt"
    trace.write_text("0:oops\n")
    assert verifier_cli.main([str(cfg), str(trace)]) == 1
    captured = capsys.readouterr()
    assert "invalid trace" in captured.out


def test_verifier_cli_invalid_config(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    cfg = tmp_path / "conf.txt"
    cfg.write_text("bad\n")
    trace = tmp_path / "trace.txt"
    trace.write_text("")
    assert verifier_cli.main([str(cfg), str(trace)]) == 1
    captured = capsys.readouterr()
    assert "invalid config" in captured.out.lower()


def test_verifier_cli_invalid_config_runtime(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: MonkeyPatch
) -> None:
    cfg = tmp_path / "conf.txt"
    cfg.write_text("a:1\nproc:(a:1):(b:1):1\n")
    trace = tmp_path / "trace.txt"
    trace.write_text("0:proc\n")

    def fake_verify_files(*args, **kwargs):
        raise parser.ParseError("bad")

    monkeypatch.setattr(verifier_cli, "verify_files", fake_verify_files)
    assert verifier_cli.main([str(cfg), str(trace)]) == 1
    captured = capsys.readouterr()
    assert "invalid config" in captured.out.lower()


def test_cli_valid(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    config = tmp_path / "conf.txt"
    config.write_text("a:1\nproc:(a:1):(b:1):1\n")
    trace_path = tmp_path / "trace.txt"
    assert cli.main([str(config), "5", "--trace", str(trace_path)]) == 0
    captured = capsys.readouterr()
    assert "Nice file! 1 process, 2 stocks, 0 to optimize" in captured.out
    assert "Main walk:" in captured.out
    assert "Final Stocks:" in captured.out
    assert "0:proc" in captured.out
    assert trace_path.read_text().splitlines() == ["0:proc"]


def test_cli_lists_all_stocks(capsys: CaptureFixture[str]) -> None:
    exit_code = cli.main([str(Path("resources/simple")), "100"])
    captured = capsys.readouterr()
    assert exit_code == 0
    lines = captured.out.splitlines()
    idx = lines.index("Final Stocks:")
    stocks = {
        line.split(" => ")[0].strip()
        for line in lines[idx + 1 : idx + 5]
        if " => " in line
    }
    assert stocks == {"client_content", "euro", "materiel", "produit"}


def test_cli_header_stock_count(capsys: CaptureFixture[str]) -> None:
    exit_code = cli.main([str(Path("resources/simple")), "100"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Nice file! 3 processes, 4 stocks, 1 to optimize" in captured.out


def test_cli_stock_alignment(capsys: CaptureFixture[str]) -> None:
    exit_code = cli.main([str(Path("resources/simple")), "100"])
    captured = capsys.readouterr()
    assert exit_code == 0
    lines = captured.out.splitlines()
    idx = lines.index("Final Stocks:")
    stock_lines = [line for line in lines[idx + 1 : idx + 5] if "=>" in line]
    assert stock_lines
    arrow_pos = stock_lines[0].index("=>")
    for line in stock_lines:
        assert line.startswith("  ")
        assert line.index("=>") == arrow_pos


def test_cli_max_time(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    config = tmp_path / "conf.txt"
    config.write_text("a:1\nproc:(a:1):(b:1):1\n")
    trace_path = tmp_path / "trace.txt"
    delay = 1
    assert cli.main([str(config), str(delay), "--trace", str(trace_path)]) == 1
    captured = capsys.readouterr()
    assert f"Max time reached at time {delay}" in captured.out
    assert "b  => 1" in captured.out


def test_cli_self_production_trace(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    trace_path = tmp_path / "self.trace"
    assert cli.main(["resources/self", "3", "--trace", str(trace_path)]) == 1
    output = capsys.readouterr().out
    assert "X  => 8" in output
    assert trace_path.read_text().splitlines() == [
        "0:genX",
        "1:genX",
        "1:genX",
        "2:genX",
        "2:genX",
        "2:genX",
        "2:genX",
    ]
    assert verifier_cli.main(["resources/self", str(trace_path)]) == 0


@pytest.mark.parametrize("existing_trace", [False, True])
def test_cli_self_50_saves_a_valid_bounded_solution(
    tmp_path: Path,
    capsys: CaptureFixture[str],
    existing_trace: bool,
) -> None:
    trace_path = tmp_path / "self.trace"
    if existing_trace:
        trace_path.write_text("previous trace\n")
    assert cli.main(["resources/self", "50", "--trace", str(trace_path)]) == 0
    output = capsys.readouterr().out
    assert "Recherche bornée au temps 17" in output
    assert "optimalité non garantie" in output
    assert "Final Stocks:" in output
    assert "X  => 100001" in output
    assert "simulation limit:" not in output
    assert "No more process doable" not in output
    assert "Deadlock" not in output
    lines = trace_path.read_text().splitlines()
    assert len(lines) == 100_000
    assert lines[:3] == ["0:genX", "1:genX", "1:genX"]
    assert lines[-1] == "16:genX"
    replay = verify_files(Path("resources/self"), trace_path)
    assert replay.stocks == {"X": 100_001}
    assert replay.time == 17


@pytest.mark.parametrize("objective", ["", "optimize:(a)\n"])
def test_cli_deadlock(
    tmp_path: Path, capsys: CaptureFixture[str], objective: str
) -> None:
    config = tmp_path / "conf.txt"
    config.write_text("a:0\nproc:(a:1):(a:1):1\n" + objective)
    trace_path = tmp_path / "trace.txt"
    assert cli.main([str(config), "5", "--trace", str(trace_path)]) == 1
    captured = capsys.readouterr()
    assert "Deadlock detected" in captured.out


@pytest.mark.parametrize("optimized", [False, True])
def test_cli_loop_with_and_without_objective(
    tmp_path: Path, capsys: CaptureFixture[str], optimized: bool
) -> None:
    config = tmp_path / "loop"
    objective = "optimize:(item)\n" if optimized else ""
    config.write_text("item:1\nloop:(item:1):(item:1):1\n" + objective)
    trace_path = tmp_path / "trace.txt"

    assert cli.main([str(config), "25", "--trace", str(trace_path)]) == (
        0 if optimized else 1
    )
    output = capsys.readouterr().out
    assert "Deadlock" not in output
    assert "item  => 1" in output
    if optimized:
        assert "Aucun plan améliorant trouvé par l’heuristique au temps 0" in output
        assert "Max time reached" not in output
        assert "No more process doable" not in output
        assert trace_path.read_text().splitlines() == [
            "# no process executed (optimization)"
        ]
    else:
        assert "Max time reached at time 25" in output
        assert "Aucune amélioration" not in output
        assert trace_path.read_text().splitlines() == [f"{i}:loop" for i in range(25)]
    assert verifier_cli.main([str(config), str(trace_path)]) == 0


def test_cli_path_traversal(tmp_path: Path) -> None:
    config = tmp_path / "conf.txt"
    config.write_text("a:1\nproc:(a:1):(b:1):1\n")
    bad_path = config.parent / ".." / config.name
    with pytest.raises(SystemExit) as exc:
        cli.main([str(bad_path), "1"])
    assert exc.value.code == 2


def test_cli_unreadable_file(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    config = tmp_path / "conf.txt"
    config.write_text("a:1\nproc:(a:1):(b:1):1\n")
    original = os.access

    def fake_access(path: os.PathLike[str] | str, mode: int) -> bool:
        if Path(path) == config:
            return False
        return original(path, mode)

    monkeypatch.setattr(os, "access", fake_access)
    with pytest.raises(SystemExit) as exc:
        cli.main([str(config), "1"])
    assert exc.value.code == 2


@pytest.mark.parametrize(
    "file",
    [
        Path("resources/bad_stock"),
        Path("resources/bad_proc"),
    ],
)
def test_cli_invalid_config(file: Path, capsys: CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main([str(file), "10"])
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "invalid config" in captured.out.lower()


@pytest.mark.parametrize(
    "resource,delay",
    [
        ("ikea", 100),
        ("steak", 100),
        ("pomme", 100),
        ("recre", 100),
        ("time", 100),
        ("finite", 100),
    ],
)
def test_cli_run_resources(
    resource: str, delay: int, capsys: CaptureFixture[str]
) -> None:
    res = Path("resources") / resource
    exit_code = cli.main([str(res), str(delay)])
    captured = capsys.readouterr()
    assert exit_code in (0, 1)
    assert "Final Stocks:" in captured.out


def test_cli_accepts_zero_delay_process_resource(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    trace_path = tmp_path / "trace.txt"
    exit_code = cli.main(
        [
            str(Path("resources/delay0")),
            "10",
            "--trace",
            str(trace_path),
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "0:instant" in captured.out
    assert "stockB  => 1" in captured.out
    assert verifier_cli.main([str(Path("resources/delay0")), str(trace_path)]) == 0


def test_cli_partial_execution_small_delay(
    capsys: CaptureFixture[str],
) -> None:
    # Delay must allow the delivery process at cycle 40 so client_content equals 1
    delay = 60
    exit_code = cli.main([str(Path("resources/simple")), str(delay)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Max time reached" not in captured.out
    assert "0:achat_materiel" in captured.out
    assert "10:realisation_produit" in captured.out
    assert "client_content  => 1" in captured.out


def test_cli_ignore_delay_when_optimize_time_first(
    capsys: CaptureFixture[str],
) -> None:
    exit_code = cli.main([str(Path("resources/simple")), "10"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Max time reached" not in captured.out
    assert "40:livraison" in captured.out
    assert "client_content  => 1" in captured.out


@pytest.mark.parametrize("option", ["--analysis-log", "--log", "--verbose", "-v"])
@pytest.mark.parametrize("command", [cli, verifier_cli])
def test_cli_rejects_removed_logging_options(command: ModuleType, option: str) -> None:
    with pytest.raises(SystemExit) as exc:
        command.build_parser().parse_args(["resources/simple", "10", option])
    assert exc.value.code == 2
