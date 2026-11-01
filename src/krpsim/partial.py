"""Production intermédiaire prudente après l'échec d'un plan complet."""

from __future__ import annotations

from .parser import Config, Process


class PartialPlanner:
    """Choisit des étapes réalisables sans sacrifier objectifs ni catalyseurs.

    Ce repli ne recherche pas d'optimum : il préfère les conversions disponibles
    aux sources renouvelables et refuse de revisiter un état de stocks.
    """

    def __init__(self, config: Config, targets: tuple[str, ...]):
        self.processes = self._dependencies(config, targets)
        self.protected = set(targets) | {
            resource
            for process in config.processes.values()
            for resource, quantity in process.needs.items()
            if process.results.get(resource, 0) >= quantity
        }
        self._seen: set[tuple[tuple[str, int], ...]] = set()

    @staticmethod
    def _dependencies(config: Config, targets: tuple[str, ...]) -> list[Process]:
        pending = list(targets)
        visited: set[str] = set()
        processes: dict[str, Process] = {}
        while pending:
            resource = pending.pop()
            if resource in visited:
                continue
            visited.add(resource)
            for process in config.processes.values():
                if process.results.get(resource, 0) > process.needs.get(resource, 0):
                    processes[process.name] = process
                    pending.extend(process.needs)
        return list(processes.values())

    def _eligible(
        self, process: Process, stocks: dict[str, int], remaining: int
    ) -> bool:
        return (
            process.delay <= remaining
            and all(stocks.get(r, 0) >= q for r, q in process.needs.items())
            and all(
                process.results.get(r, 0) >= process.needs.get(r, 0)
                for r in self.protected
            )
        )

    @staticmethod
    def _priority(process: Process) -> tuple[bool, int, str]:
        conversion = any(
            quantity > process.results.get(resource, 0)
            for resource, quantity in process.needs.items()
        )
        return (not conversion, process.delay, process.name)

    def next_process(self, stocks: dict[str, int], remaining: int) -> Process | None:
        """Choisit une étape dont toutes les entrées sont présentes ensemble."""

        signature = tuple(sorted((r, q) for r, q in stocks.items() if q > 0))
        if signature in self._seen:
            return None
        self._seen.add(signature)
        candidates = [
            process
            for process in self.processes
            if self._eligible(process, stocks, remaining)
        ]
        return min(candidates, key=self._priority) if candidates else None
