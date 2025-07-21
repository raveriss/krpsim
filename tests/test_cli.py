import os
from pathlib import Path

import pytest

from krpsim import cli, verifier_cli


def test_cli_help(capsys):
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


def test_cli_invalid_delay(tmp_path):
    config = tmp_path / "conf.txt"
    config.write_text("dummy")
    with pytest.raises(SystemExit) as exc:
        cli.main([str(config), "0"])
    assert exc.value.code == 2


def test_cli_delay_help_text() -> None:
    parser = cli.build_parser()
    assert "inclusive upper bound" in parser.format_help()


def test_verifier_cli_help(capsys):
    with pytest.raises(SystemExit) as exc:
        verifier_cli.main(["-h"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "usage" in captured.out.lower()


def test_verifier_cli_valid(tmp_path, capsys):
    cfg = tmp_path / "conf.txt"
    cfg.write_text("a:1\nproc:(a:1):(b:1):1\n")
    trace = tmp_path / "trace.txt"
    trace.write_text("0:proc\n")
    assert verifier_cli.main([str(cfg), str(trace)]) == 0
    captured = capsys.readouterr()
    assert "trace is valid" in captured.out


def test_verifier_cli_error(tmp_path, capsys):
    cfg = tmp_path / "conf.txt"
    cfg.write_text("a:1\nproc:(a:1):(b:1):1\n")
    trace = tmp_path / "trace.txt"
    trace.write_text("0:oops\n")
    assert verifier_cli.main([str(cfg), str(trace)]) == 1
    captured = capsys.readouterr()
    assert "invalid trace" in captured.out


def test_cli_valid(tmp_path, capsys):
    config = tmp_path / "conf.txt"
    config.write_text("a:1\nproc:(a:1):(b:1):1\n")
    trace_path = tmp_path / "trace.txt"
    assert cli.main([str(config), "5", "--trace", str(trace_path)]) == 0
    captured = capsys.readouterr()
    assert "Nice file! 1 process, 1 stock, 0 objectives" in captured.out
    assert "Main walk:" in captured.out
    assert "Final Stocks:" in captured.out
    assert "0:proc" in captured.out
    assert trace_path.read_text().splitlines() == ["0:proc"]


def test_cli_lists_all_stocks(capsys: pytest.CaptureFixture[str]) -> None:
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


def test_cli_stock_alignment(capsys: pytest.CaptureFixture[str]) -> None:
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


def test_cli_max_time(tmp_path, capsys):
    config = tmp_path / "conf.txt"
    config.write_text("a:1\nproc:(a:1):(b:1):1\n")
    trace_path = tmp_path / "trace.txt"
    delay = 1
    assert cli.main([str(config), str(delay), "--trace", str(trace_path)]) == 1
    captured = capsys.readouterr()
    assert f"Max time reached at time {delay}" in captured.out
    assert "b  => 1" in captured.out


def test_cli_deadlock(tmp_path, capsys):
    config = tmp_path / "conf.txt"
    config.write_text("a:0\nproc:(a:1):(a:1):1\n")
    trace_path = tmp_path / "trace.txt"
    assert cli.main([str(config), "5", "--trace", str(trace_path)]) == 1
    captured = capsys.readouterr()
    assert "Deadlock detected" in captured.out


def test_cli_verbose_and_log(tmp_path):
    config = tmp_path / "conf.txt"
    config.write_text("a:1\nproc:(a:1):(b:1):1\n")
    trace_path = tmp_path / "trace.txt"
    log_path = tmp_path / "app.log"
    assert (
        cli.main(
            [
                str(config),
                "5",
                "--trace",
                str(trace_path),
                "--verbose",
                "--log",
                str(log_path),
            ]
        )
        == 0
    )
    assert "0:proc" in log_path.read_text()


def test_cli_path_traversal(tmp_path):
    config = tmp_path / "conf.txt"
    config.write_text("a:1\nproc:(a:1):(b:1):1\n")
    bad_path = config.parent / ".." / config.name
    with pytest.raises(SystemExit) as exc:
        cli.main([str(bad_path), "1"])
    assert exc.value.code == 2


def test_cli_unreadable_file(tmp_path, monkeypatch):
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
        Path("resources/invalid_bad_stock"),
        Path("resources/invalid_bad_process"),
    ],
)
def test_cli_invalid_config(file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main([str(file), "10"])
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "invalid config" in captured.out.lower()


def test_verifier_cli_log(tmp_path):
    cfg = tmp_path / "conf.txt"
    cfg.write_text("a:1\nproc:(a:1):(b:1):1\n")
    trace = tmp_path / "trace.txt"
    trace.write_text("0:proc\n")
    log_file = tmp_path / "verif.log"
    assert (
        verifier_cli.main([str(cfg), str(trace), "--verbose", "--log", str(log_file)])
        == 0
    )
    assert "trace is valid" in log_file.read_text()


@pytest.mark.parametrize(
    "resource,delay",
    [
        ("ikea", 100),
        ("steak", 100),
        ("pomme", 100),
        ("recre", 100),
        ("inception", 100),
        ("custom_finite", 100),
        ("custom_infinite", 5),
    ],
)
def test_cli_run_resources(
    resource: str, delay: int, capsys: pytest.CaptureFixture[str]
) -> None:
    res = Path("resources") / resource
    exit_code = cli.main([str(res), str(delay)])
    captured = capsys.readouterr()
    assert exit_code in (0, 1)
    if resource == "custom_infinite":
        assert exit_code == 1
        assert "Max time reached" in captured.out


def test_cli_partial_execution_small_delay(capsys: pytest.CaptureFixture[str]) -> None:
    delay = 60
    exit_code = cli.main([str(Path("resources/simple")), str(delay)])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Max time reached" in captured.out
    assert "0:achat_materiel" in captured.out
    assert "10:realisation_produit" in captured.out
    assert "client_content  => 1" in captured.out
