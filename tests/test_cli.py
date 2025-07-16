import pytest

from krpsim import cli, verifier_cli


def test_cli_help(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["-h"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out.lower()


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
    assert "Main walk" in captured.out
    assert "0:proc" in captured.out
    assert trace_path.read_text().splitlines() == ["0:proc"]
