"""Simple simulator running processes cycle by cycle."""

from __future__ import annotations

import logging
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
        self.deadlock = False
        self._max_time = 0

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

    def _start_processes(self) -> tuple[bool, bool]:
        started = False
        started_nonzero = False
        logger = logging.getLogger(__name__)
        for process in order_processes(self.config):
            if self.time + process.delay > self._max_time:
                continue
            if all(
                self.stocks.get(name, 0) >= qty for name, qty in process.needs.items()
            ):
                for name, qty in process.needs.items():
                    self.stocks[name] -= qty
                if process.delay == 0:
                    for name, qty in process.results.items():
                        self.stocks[name] = self.stocks.get(name, 0) + qty
                else:
                    self._running.append(_RunningProcess(process, process.delay))
                    started_nonzero = True
                self.trace.append((self.time, process.name))
                logger.info("%d:%s", self.time, process.name)
                started = True
        return started, started_nonzero

    def step(self) -> bool:
        running_before = bool(self._running)
        self._complete_running()
        started, started_nonzero = self._start_processes()
        advance = running_before or bool(self._running) or started_nonzero
        if advance:
            self.time += 1
        return advance

    def run(self, max_time: int) -> list[tuple[int, str]]:
        self.deadlock = False
        self._max_time = max_time
        if self._custom_strategy(max_time):
            return self.trace
        while self.time <= max_time and self.step():
            pass
        if not self.trace and self.config.processes:
            self.deadlock = True
        return self.trace

    # --- custom optimization helpers ---

    def _custom_strategy(self, max_time: int) -> bool:
        target = self._single_target()
        if not target:
            return False
        target_proc = self._target_process(target)
        if not target_proc:
            return False
        token, main_res = self._split_resources(target_proc)
        if not (token and main_res):
            return False
        booster = self._find_booster(token, main_res, target_proc)
        if not booster:  # pragma: no cover
            return False
        loops, targets = self._best_loops(booster, target_proc, main_res, max_time)
        self._apply_custom_plan(booster, target_proc, loops, targets, max_time)
        return True

    def _single_target(self) -> str | None:
        targets = [t for t in (self.config.optimize or []) if t != "time"]
        return targets[0] if len(targets) == 1 else None

    def _target_process(self, target: str) -> Process | None:
        procs = [p for p in self.config.processes.values() if p.results.get(target)]
        return procs[0] if len(procs) == 1 else None

    def _split_resources(self, proc: Process) -> tuple[str | None, str | None]:
        token = next(
            (n for n, q in proc.needs.items() if proc.results.get(n, 0) >= q),
            None,
        )
        main_res = next((n for n in proc.needs if n != token), None)
        return token, main_res

    def _find_booster(
        self, token: str, main_res: str, target_proc: Process
    ) -> Process | None:
        for proc in self.config.processes.values():
            if (
                proc is not target_proc
                and proc.needs.get(token)
                and proc.results.get(token, 0) >= proc.needs[token]
                and proc.results.get(main_res, 0) > proc.needs.get(main_res, 0)
            ):
                return proc
        return None  # pragma: no cover

    def _best_loops(
        self, booster: Process, target_proc: Process, main_res: str, max_time: int
    ) -> tuple[int, int]:
        best_loops = 0
        best_targets = 0
        init_main = self.stocks.get(main_res, 0)
        for loops in range(0, max_time // booster.delay + 1):
            time_left = max_time - loops * booster.delay
            possible_targets = time_left // target_proc.delay
            main_qty = init_main + loops * (
                booster.results.get(main_res, 0) - booster.needs.get(main_res, 0)
            )
            produced = min(
                possible_targets, main_qty // target_proc.needs.get(main_res, 0)
            )
            if produced > best_targets:
                best_targets = produced
                best_loops = loops
        return best_loops, best_targets

    def _apply_custom_plan(
        self,
        booster: Process,
        target_proc: Process,
        loops: int,
        targets: int,
        max_time: int,
    ) -> None:
        time = 0
        trace: list[tuple[int, str]] = []
        stocks = self.stocks.copy()
        for _ in range(loops):
            if time + booster.delay > max_time:  # pragma: no cover
                break
            for name, qty in booster.needs.items():
                stocks[name] -= qty
            trace.append((time, booster.name))
            time += booster.delay
            for name, qty in booster.results.items():
                stocks[name] = stocks.get(name, 0) + qty
        for _ in range(targets):
            if time + target_proc.delay > max_time:  # pragma: no cover
                break
            for name, qty in target_proc.needs.items():
                stocks[name] -= qty
            trace.append((time, target_proc.name))
            time += target_proc.delay
            for name, qty in target_proc.results.items():
                stocks[name] = stocks.get(name, 0) + qty
        self.trace = trace
        self.stocks = stocks
        self.time = time
