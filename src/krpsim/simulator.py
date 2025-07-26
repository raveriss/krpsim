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
        # custom optimization for single target cases with resource farming
        if self.config.optimize and (
            (len(self.config.optimize) == 1 and self.config.optimize[0] != "time")
            or (
                len(self.config.optimize) == 2
                and self.config.optimize[0] == "time"
                and self.config.optimize[1] != "time"
            )
        ):
            target = (
                self.config.optimize[0]
                if self.config.optimize[0] != "time"
                else self.config.optimize[1]
            )
            target_proc = next(
                (p for p in self.config.processes.values() if p.results.get(target)),
                None,
            )
            if (
                target_proc
                and len(
                    [p for p in self.config.processes.values() if p.results.get(target)]
                )
                == 1
            ):
                token = next(
                    (
                        n
                        for n, q in target_proc.needs.items()
                        if target_proc.results.get(n, 0) >= q
                    ),
                    None,
                )
                main_res = next(
                    (n for n in target_proc.needs if n != token),
                    None,
                )
                booster = None
                if token and main_res:
                    for p in self.config.processes.values():
                        if (
                            p is not target_proc
                            and p.needs.get(token)
                            and p.results.get(token, 0) >= p.needs[token]
                            and p.results.get(main_res, 0) > p.needs.get(main_res, 0)
                        ):
                            booster = p
                            break
                if booster and main_res:
                    best_loops = 0
                    best_targets = 0
                    init_main = self.stocks.get(main_res, 0)
                    for loops in range(0, max_time // booster.delay + 1):
                        time_left = max_time - loops * booster.delay
                        possible_targets = time_left // target_proc.delay
                        main_qty = init_main + loops * (
                            booster.results.get(main_res, 0)
                            - booster.needs.get(main_res, 0)
                        )
                        produced = min(
                            possible_targets,
                            main_qty // target_proc.needs.get(main_res, 0),
                        )
                        if produced > best_targets:
                            best_targets = produced
                            best_loops = loops

                    time = 0
                    trace: list[tuple[int, str]] = []
                    stocks = self.stocks.copy()
                    for _ in range(best_loops):
                        if time + booster.delay > max_time:  # pragma: no cover
                            break
                        for n, q in booster.needs.items():
                            stocks[n] -= q
                        trace.append((time, booster.name))
                        time += booster.delay
                        for n, q in booster.results.items():
                            stocks[n] = stocks.get(n, 0) + q
                    for _ in range(best_targets):
                        if time + target_proc.delay > max_time:  # pragma: no cover
                            break
                        for n, q in target_proc.needs.items():
                            stocks[n] -= q
                        trace.append((time, target_proc.name))
                        time += target_proc.delay
                        for n, q in target_proc.results.items():
                            stocks[n] = stocks.get(n, 0) + q
                    self.trace = trace
                    self.stocks = stocks
                    self.time = time
                    return self.trace
       
        while self.time <= max_time and self.step():
            pass
        if not self.trace and self.config.processes:
            self.deadlock = True
        return self.trace
