from pathlib import Path

import pytest

from krpsim import parser


def test_parse_valid_simple():
    cfg = parser.parse_file(Path("resources/simple"))
    assert cfg.stocks["euro"] == 10
    assert "achat_materiel" in cfg.processes
    assert "realisation_produit" in cfg.processes


@pytest.mark.parametrize("fname", ["invalid_bad_stock", "invalid_bad_process"])
def test_parse_invalid_files(fname):
    with pytest.raises(parser.ParseError):
        parser.parse_file(Path("resources") / fname)


def test_parse_duplicate_entries(tmp_path):
    config = tmp_path / "dup.txt"
    config.write_text("a:1\na:2\nproc:(a:1):(b:1):1\n")  # duplicate stock
    with pytest.raises(parser.ParseError):
        parser.parse_file(config)

    config.write_text(
        "a:1\nproc:(a:1):(b:1):1\nproc:(a:1):(b:1):1\n"  # duplicate process
    )
    with pytest.raises(parser.ParseError):
        parser.parse_file(config)


def test_parse_unrecognized_line(tmp_path):
    config = tmp_path / "bad.txt"
    config.write_text("a:1\nunknown\nproc:(a:1):(b:1):1\n")
    with pytest.raises(parser.ParseError):
        parser.parse_file(config)


def test_parse_resources_edge_cases():
    assert parser._parse_resources("") == {}
    with pytest.raises(parser.ParseError):
        parser._parse_resources("a:bad")

    with pytest.raises(parser.ParseError):
        parser._parse_resources("a:-1")
    with pytest.raises(parser.ParseError):
        parser._parse_resources("a:1;a:2")


def test_parse_optimize():
    cfg = parser.parse_file(Path("resources/simple"))
    assert cfg.optimize == ["time", "client_content"]


def test_parse_optimize_errors(tmp_path):
    config = tmp_path / "opt.txt"
    config.write_text("a:1\nproc:(a:1):(b:1):1\noptimize:(c)\n")
    with pytest.raises(parser.ParseError):
        parser.parse_file(config)

    config.write_text("a:1\nproc:(a:1):(b:1):1\noptimize:(time;time)\n")
    with pytest.raises(parser.ParseError):
        parser.parse_file(config)

    config.write_text("a:1\nproc:(a:1):(b:1):1\noptimize:(time)\noptimize:(time)\n")
    with pytest.raises(parser.ParseError):
        parser.parse_file(config)
