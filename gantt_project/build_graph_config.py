"""Build a JSON graph configuration from a krpsim config and trace file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from krpsim import parser as parser_mod


def parse_trace(trace_path: Path) -> list[tuple[int, str]]:
    """Parse trace lines in the form ``cycle:process``."""
    entries: list[tuple[int, str]] = []
    for index, raw_line in enumerate(trace_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        cycle_text, sep, process_name = line.partition(":")
        process_name = process_name.strip()
        if sep != ":" or not cycle_text.isdigit() or not process_name:
            raise ValueError(f"invalid trace line {index}: '{raw_line}'")
        entries.append((int(cycle_text), process_name))
    return entries


def build_payload(config_path: Path, trace_path: Path) -> dict[str, object]:
    """Create the JSON payload consumed by the Gantt renderer."""
    config = parser_mod.parse_file(config_path)
    trace_entries = parse_trace(trace_path)

    tasks: list[dict[str, object]] = []
    for start, process_name in trace_entries:
        process = config.processes.get(process_name)
        if process is None:
            raise ValueError(f"unknown process in trace: '{process_name}'")
        tasks.append(
            {
                "Task": process_name,
                "Start": start,
                "Duration": process.delay,
            }
        )

    config_stem = config_path.stem if config_path.stem else config_path.name
    return {
        "title": f"Diagramme de Gantt - {config_stem}",
        "tasks": tasks,
        "config_file": str(config_path),
        "trace_file": str(trace_path),
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(prog="build_graph_config")
    parser.add_argument("--config", required=True, help="krpsim config file path")
    parser.add_argument("--trace", required=True, help="krpsim trace file path")
    parser.add_argument("--output", required=True, help="json output file path")
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    trace_path = Path(args.trace)
    output_path = Path(args.output)

    if not config_path.is_file():
        print(f"invalid config path: '{config_path}'", file=sys.stderr)
        return 1
    if not trace_path.is_file():
        print(f"invalid trace path: '{trace_path}'", file=sys.stderr)
        return 1

    payload = build_payload(config_path, trace_path)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[GRAPH_CONFIG] Fichier genere: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
