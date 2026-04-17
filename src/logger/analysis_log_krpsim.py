"""Structured analysis logs for `krpsim` CLI instrumentation."""

from __future__ import annotations

from pprint import pformat
from typing import Iterable


class AnalysisLogger:
    """Verbose logger dedicated to CLI behaviour analysis."""

    GRAPHICAL_SEPARATOR = (
        "/*   -'-,-'-,-'-,-'-,-'-,-'-,-'-,-'-,-'-,-'-,-'-,-'-,-'-,-'-,-'-,-'-,-',-'   */"
    )
    SUBHEADER_SEPARATOR = "/*   -'-,-'-,-'-,-'-,-'-,-   */"
    VALUE_SEPARATOR = "--------------------------------------------------------------"
    SUBHEADER_PADDING = " " * 24

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def _emit(self, message: str = "") -> None:
        if not self.enabled:
            return
        print(message)

    def _format_value(self, value: object) -> str:
        return pformat(value, compact=False, sort_dicts=False)

    def _format_scope(self, scope: str | None) -> str:
        if not scope:
            return ""
        return f"[{scope}] "

    def _log_graphical_separator(self) -> None:
        self._emit(self.GRAPHICAL_SEPARATOR)

    def log_header(self, title: str, scope: str | None = None) -> None:
        if not self.enabled:
            return
        scope_prefix = self._format_scope(scope)
        full_title = f"{scope_prefix}{title}" if scope_prefix else title
        self._emit("")
        self._log_graphical_separator()
        self._emit(f"/* {full_title.center(68)} */")
        self._log_graphical_separator()
        self._emit("")

    def log_subheader(self, title: str, scope: str | None = None) -> None:
        if not self.enabled:
            return
        scope_prefix = self._format_scope(scope)
        full_title = f"{scope_prefix}{title}" if scope_prefix else title
        self._emit(f"{self.SUBHEADER_PADDING}{self.SUBHEADER_SEPARATOR}")
        self._emit(f"{self.SUBHEADER_PADDING}/* {full_title.center(26)} */")
        self._emit(f"{self.SUBHEADER_PADDING}{self.SUBHEADER_SEPARATOR}")

    def log_step(
        self,
        label: str,
        detail: object | None = None,
        scope: str | None = None,
    ) -> None:
        if not self.enabled:
            return
        scope_prefix = self._format_scope(scope)
        if detail is None:
            self._emit(f"{scope_prefix}[STEP] {label}")
            return
        self._emit(f"{scope_prefix}[STEP] {label}: {self._format_value(detail)}")

    def log_key_value(
        self,
        label: str,
        value: object,
        scope: str | None = None,
    ) -> None:
        if not self.enabled:
            return
        scope_prefix = self._format_scope(scope)
        formatted = self._format_value(value)
        if "\n" in formatted:
            self._emit(f"{scope_prefix}{label} :")
            self._emit(formatted)
        else:
            self._emit(f"{scope_prefix}{label} : {formatted}")
        self._emit("")

    def log_calculation(
        self,
        label: str,
        steps: Iterable[str],
        result: object,
        scope: str | None = None,
    ) -> None:
        if not self.enabled:
            return
        scope_prefix = self._format_scope(scope)
        self._emit(f"{scope_prefix}{label}")
        self._emit(f"{scope_prefix}CALCULE :")
        for step in steps:
            self._emit(step)
        self._emit(self.VALUE_SEPARATOR)
        self._emit(f"= {self._format_value(result)}")
        self._emit("")
