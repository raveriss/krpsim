"""Simple simulator running processes cycle by cycle."""

from __future__ import annotations

from dataclasses import dataclass

from .optimizer import order_processes
from .parser import Config, Process


@dataclass
class _RunningProcess:
    process: Process
    remaining: int


class Simulator:
    """Run processes from a :class:`Config` over discrete cycles."""

    def __init__(self, config: Config):
        self.config = config
        self.stocks: dict[str, int] = config.stocks.copy()
        self.time = 0
        self._running: list[_RunningProcess] = []
        self.trace: list[tuple[int, str]] = []

    def _complete_running(self) -> None:
        completed: list[_RunningProcess] = []
        for rp in self._running:
            rp.remaining -= 1
            if rp.remaining == 0:
                for name, qty in rp.process.results.items():
                    self.stocks[name] = self.stocks.get(name, 0) + qty
                completed.append(rp)
        for rp in completed:
            self._running.remove(rp)

    def _start_processes(self) -> bool:
        started = False
        for process in order_processes(self.config):
            if all(
                self.stocks.get(name, 0) >= qty for name, qty in process.needs.items()
            ):
                for name, qty in process.needs.items():
                    self.stocks[name] -= qty
                self._running.append(_RunningProcess(process, process.delay))
                self.trace.append((self.time, process.name))
                started = True
        return started

    def step(self) -> bool:
        self._complete_running()
        started = self._start_processes()
        self.time += 1
        return started or bool(self._running)

    def run(self, max_time: int) -> list[tuple[int, str]]:
        while self.time < max_time and self.step():
            pass
        return self.trace
