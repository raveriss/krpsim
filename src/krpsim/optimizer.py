"""Process ordering logic for the simulator (Agent 3)."""

from __future__ import annotations

from .parser import Config, Process


def order_processes(config: Config) -> list[Process]:
    """Return processes sorted according to ``config.optimize``."""

    def sort_key(proc: Process) -> tuple[int | str, ...]:
        key: list[int | str] = []
        if config.optimize:
            for target in config.optimize:
                if target == "time":
                    key.append(proc.delay)
                else:
                    key.append(-proc.results.get(target, 0))
        key.append(proc.name)
        return tuple(key)

    return sorted(config.processes.values(), key=sort_key)
