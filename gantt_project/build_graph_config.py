"""Build a JSON graph configuration from a krpsim config and trace file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from krpsim import parser as parser_mod
from krpsim.parser import Config
from logger.analysis_log_gantt_project import (
    AnalysisLogger,
    get_active_analysis_logger,
    set_active_analysis_logger,
)


def _serialize_config(config: Config) -> dict[str, object]:
    """Return a readable representation of the source KRPSIM config."""
    return {
        "stocks": config.stocks,
        "processes": {
            name: {
                "name": process.name,
                "needs": process.needs,
                "results": process.results,
                "delay": process.delay,
            }
            for name, process in config.processes.items()
        },
        "optimize": config.optimize,
    }


def parse_trace(trace_path: Path) -> list[tuple[int, str]]:
    """Parse trace lines in the form ``cycle:process``."""
    analysis_logger = get_active_analysis_logger()
    scope = "build_graph_config.parse_trace"
    analysis_logger.log_header("TRACE PARSING", scope=scope)
    analysis_logger.log_key_value("TRACE_PATH", str(trace_path), scope=scope)
    raw_lines = trace_path.read_text(encoding="utf-8").splitlines()
    analysis_logger.log_key_value("RAW_TRACE_LINES", raw_lines, scope=scope)
    entries: list[tuple[int, str]] = []
    for index, raw_line in enumerate(raw_lines, start=1):
        line = raw_line.strip()
        analysis_logger.log_key_value(
            "TRACE_LINE_READ",
            {"line_number": index, "raw": raw_line, "normalized": line},
            scope=scope,
        )
        if not line or line.startswith("#"):
            analysis_logger.log_step(
                "TRACE_LINE_SKIPPED",
                {
                    "line_number": index,
                    "reason": "empty_or_comment",
                },
                scope=scope,
            )
            continue
        cycle_text, sep, process_name = line.partition(":")
        process_name = process_name.strip()
        if sep != ":" or not cycle_text.isdigit() or not process_name:
            analysis_logger.log_step(
                "TRACE_LINE_ERROR",
                {
                    "line_number": index,
                    "cycle": cycle_text,
                    "separator": sep,
                    "process": process_name,
                },
                scope=scope,
            )
            raise ValueError(f"invalid trace line {index}: '{raw_line}'")
        entry = (int(cycle_text), process_name)
        analysis_logger.log_key_value("TRACE_ENTRY_PARSED", entry, scope=scope)
        entries.append(entry)
    analysis_logger.log_key_value("PARSED_TRACE_ENTRIES", entries, scope=scope)
    return entries


def build_payload(config_path: Path, trace_path: Path) -> dict[str, object]:
    """Create the JSON payload consumed by the Gantt renderer."""
    analysis_logger = get_active_analysis_logger()
    scope = "build_graph_config.build_payload"
    analysis_logger.log_header("GRAPH CONFIG PAYLOAD", scope=scope)
    analysis_logger.log_key_value("CONFIG_PATH", str(config_path), scope=scope)
    analysis_logger.log_key_value("TRACE_PATH", str(trace_path), scope=scope)
    config = parser_mod.parse_file(config_path)
    analysis_logger.log_key_value(
        "PARSED_CONFIG",
        _serialize_config(config),
        scope=scope,
    )
    trace_entries = parse_trace(trace_path)
    analysis_logger.log_key_value("TRACE_ENTRIES", trace_entries, scope=scope)

    tasks: list[dict[str, object]] = []
    for start, process_name in trace_entries:
        process = config.processes.get(process_name)
        analysis_logger.log_key_value(
            "PROCESS_LOOKUP",
            {
                "start": start,
                "process_name": process_name,
                "process_found": process is not None,
                "process_delay": process.delay if process else None,
            },
            scope=scope,
        )
        if process is None:
            analysis_logger.log_step(
                "UNKNOWN_PROCESS_ERROR",
                process_name,
                scope=scope,
            )
            raise ValueError(f"unknown process in trace: '{process_name}'")
        task = {
            "Task": process_name,
            "Start": start,
            "Duration": process.delay,
        }
        analysis_logger.log_key_value("TASK_CREATED", task, scope=scope)
        tasks.append(task)

    config_stem = config_path.stem if config_path.stem else config_path.name
    payload = {
        "title": f"Diagramme de Gantt - {config_stem}",
        "tasks": tasks,
        "config_file": str(config_path),
        "trace_file": str(trace_path),
    }
    analysis_logger.log_key_value("PAYLOAD", payload, scope=scope)
    return payload


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(prog="build_graph_config")
    parser.add_argument("--config", required=True, help="krpsim config file path")
    parser.add_argument("--trace", required=True, help="krpsim trace file path")
    parser.add_argument("--output", required=True, help="json output file path")
    parser.add_argument(
        "--analysis-log",
        action="store_true",
        help="print detailed analysis logs for graph config generation",
    )
    args = parser.parse_args(argv)
    analysis_logger = AnalysisLogger(enabled=args.analysis_log)
    set_active_analysis_logger(analysis_logger)
    scope = "build_graph_config.main"
    analysis_logger.log_header("CLI ENTRYPOINT", scope=scope)
    analysis_logger.log_key_value("PARSED_ARGS", vars(args), scope=scope)

    config_path = Path(args.config)
    trace_path = Path(args.trace)
    output_path = Path(args.output)
    analysis_logger.log_header("INPUT VALIDATION", scope=scope)
    analysis_logger.log_key_value("CONFIG_PATH", str(config_path), scope=scope)
    analysis_logger.log_key_value("TRACE_PATH", str(trace_path), scope=scope)
    analysis_logger.log_key_value("OUTPUT_PATH", str(output_path), scope=scope)

    if not config_path.is_file():
        analysis_logger.log_step(
            "CONFIG_PATH_ERROR",
            str(config_path),
            scope=scope,
        )
        print(f"invalid config path: '{config_path}'", file=sys.stderr)
        return 1
    if not trace_path.is_file():
        analysis_logger.log_step(
            "TRACE_PATH_ERROR",
            str(trace_path),
            scope=scope,
        )
        print(f"invalid trace path: '{trace_path}'", file=sys.stderr)
        return 1

    payload = build_payload(config_path, trace_path)
    output_text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    analysis_logger.log_header("OUTPUT WRITE", scope=scope)
    analysis_logger.log_key_value("OUTPUT_PATH", str(output_path), scope=scope)
    analysis_logger.log_key_value("OUTPUT_TEXT", output_text, scope=scope)
    output_path.write_text(
        output_text,
        encoding="utf-8",
    )
    analysis_logger.log_step("WRITE_DONE", str(output_path), scope=scope)
    analysis_logger.log_key_value("EXIT_CODE", 0, scope=scope)
    print(f"[GRAPH_CONFIG] Fichier genere: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
