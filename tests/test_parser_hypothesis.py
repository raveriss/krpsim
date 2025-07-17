from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from krpsim import parser


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(data=st.text())
def test_parse_random_utf8_does_not_crash(tmp_path: Path, data: str) -> None:
    cfg = tmp_path / "conf.txt"
    cfg.write_text(data)
    try:
        parser.parse_file(cfg)
    except parser.ParseError:
        pass


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(data=st.binary())
def test_parse_random_binary_does_not_crash(tmp_path: Path, data: bytes) -> None:
    cfg = tmp_path / "conf.txt"
    cfg.write_bytes(data)
    try:
        parser.parse_file(cfg)
    except parser.ParseError:
        pass


@settings(max_examples=25, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    line=st.text(
        st.characters(
            blacklist_characters="\n\r",
            blacklist_categories={"Cs"},
        ),
        min_size=256,
        max_size=512,
    )
)
def test_parse_long_line_always_rejected(tmp_path: Path, line: str) -> None:
    cfg = tmp_path / "conf.txt"
    cfg.write_text(line + "\n")
    with pytest.raises(parser.ParseError):
        parser.parse_file(cfg)
