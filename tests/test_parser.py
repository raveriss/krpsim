import os
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


def test_parse_nonexistent_path(tmp_path):
    with pytest.raises(parser.ParseError):
        parser.parse_file(tmp_path / "doesnotexist")


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


def test_internal_parser_functions(tmp_path):
    with pytest.raises(parser.ParseError):
        parser._parse_stock("bad")
    with pytest.raises(parser.ParseError):
        parser._parse_stock("a:-1")
    with pytest.raises(parser.ParseError):
        parser._parse_process("bad")
    with pytest.raises(parser.ParseError):
        parser._parse_optimize("bad")

    empty = tmp_path / "empty.txt"
    empty.write_text("")
    with pytest.raises(parser.ParseError):
        parser.parse_file(empty)

    config = tmp_path / "tmp.txt"
    config.write_text("a:1\nproc:(a:1):(b:1):1\noptimize:(time;time)\n")
    with pytest.raises(parser.ParseError):
        parser.parse_file(config)

    config.write_text("a:1\nproc:(a:1):(b:1):1\noptimize:(time)\noptimize:(time)\n")
    with pytest.raises(parser.ParseError):
        parser.parse_file(config)


def test_parse_non_utf8_file(tmp_path):
    bad = tmp_path / "bad.txt"
    bad.write_bytes(b"\x80\xa0")
    with pytest.raises(parser.ParseError):
        parser.parse_file(bad)


def test_parse_bom_rejected(tmp_path):
    data = b"\xef\xbb\xbf" + b"a:1\nproc:(a:1):(b:1):1\n"
    cfg = tmp_path / "bom.txt"
    cfg.write_bytes(data)
    with pytest.raises(parser.ParseError):
        parser.parse_file(cfg)


def test_parse_crlf_rejected(tmp_path):
    data = b"a:1\r\nproc:(a:1):(b:1):1\r\n"
    cfg = tmp_path / "crlf.txt"
    cfg.write_bytes(data)
    with pytest.raises(parser.ParseError):
        parser.parse_file(cfg)


def test_parse_long_line_rejected(tmp_path):
    long_line = b"a" * 256 + b"\n"
    cfg = tmp_path / "long.txt"
    cfg.write_bytes(long_line)
    with pytest.raises(parser.ParseError):
        parser.parse_file(cfg)


class _FakeQty(str):
    def isdigit(self) -> bool:
        return True


class _FakeLine:
    def split(self, sep: str, maxsplit: int = 1) -> list[str]:
        return ["a", _FakeQty("-1")]


def test_parse_stock_negative() -> None:
    with pytest.raises(parser.ParseError):
        parser._parse_stock(_FakeLine())  # type: ignore[arg-type]


def test_parse_resources_edge_cases_continued():
    assert parser._parse_resources("a:1;;b:1") == {"a": 1, "b": 1}
    with pytest.raises(parser.ParseError):
        parser._parse_resources("a:0")


def test_parse_optimize_empty():
    with pytest.raises(parser.ParseError):
        parser._parse_optimize("optimize:()")


def test_parse_path_traversal(tmp_path):
    cfg = tmp_path / "conf.txt"
    cfg.write_text("a:1\nproc:(a:1):(b:1):1\n")
    bad = cfg.parent / ".." / cfg.name
    with pytest.raises(parser.ParseError):
        parser.parse_file(bad)


def test_parse_unreadable_file(tmp_path, monkeypatch):
    cfg = tmp_path / "conf.txt"
    cfg.write_text("a:1\nproc:(a:1):(b:1):1\n")

    original = os.access

    def fake_access(path: os.PathLike[str] | str, mode: int) -> bool:
        if Path(path) == cfg:
            return False
        return original(path, mode)

    monkeypatch.setattr(os, "access", fake_access)
    with pytest.raises(parser.ParseError):
        parser.parse_file(cfg)
