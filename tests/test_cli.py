from krpsim import cli, verifier_cli


def test_cli_main(capsys):
    cli.main()
    captured = capsys.readouterr()
    assert "krpsim CLI placeholder" in captured.out


def test_verifier_cli_main(capsys):
    verifier_cli.main()
    captured = capsys.readouterr()
    assert "krpsim verifier placeholder" in captured.out
