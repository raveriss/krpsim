from krpsim import cli, verifier_cli


def test_cli_main(capsys):
    assert cli.main([]) == 0
    captured = capsys.readouterr()
    assert "krpsim CLI placeholder" in captured.out


def test_verifier_cli_main(capsys):
    assert verifier_cli.main([]) == 0
    captured = capsys.readouterr()
    assert "krpsim verifier placeholder" in captured.out
