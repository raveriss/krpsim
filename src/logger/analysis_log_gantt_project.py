"""Structured analysis logs for Gantt graph generation instrumentation."""

from __future__ import annotations

from logger.analysis_log_krpsim import AnalysisLogger

__all__ = [
    "AnalysisLogger",
    "get_active_analysis_logger",
    "set_active_analysis_logger",
]

_ACTIVE_ANALYSIS_LOGGER: AnalysisLogger | None = None


def set_active_analysis_logger(logger: AnalysisLogger | None) -> None:
    """Definit l'instance de logger d'analyse active pour le process courant."""
    global _ACTIVE_ANALYSIS_LOGGER
    _ACTIVE_ANALYSIS_LOGGER = logger


def get_active_analysis_logger() -> AnalysisLogger:
    """Retourne le logger d'analyse actif, ou un logger no-op par defaut."""
    global _ACTIVE_ANALYSIS_LOGGER
    if _ACTIVE_ANALYSIS_LOGGER is None:
        _ACTIVE_ANALYSIS_LOGGER = AnalysisLogger(enabled=False)
    return _ACTIVE_ANALYSIS_LOGGER
