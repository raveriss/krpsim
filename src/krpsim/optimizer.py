"""Strategie de tri des processus avant lancement en simulation.

Ce module isole la politique d'ordonnancement pour pouvoir faire evoluer
la priorisation sans diffuser des effets de bord dans le simulateur.
"""

# Pour retarder l'evaluation des types et limiter les cycles.
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

from logger.analysis_log_krpsim import get_active_analysis_logger

# Pour limiter le couplage aux composants internes necessaires.
from .parser import Config, Process


@dataclass(frozen=True)
class BatchPlan:
    """Plan materialise pour une production elementaire de l'objectif."""

    counts: dict[str, int]
    expected_gain: tuple[int, ...]


@dataclass(frozen=True)
class _BatchCandidate:
    """Candidate interne évalué avant sélection du meilleur lot."""

    quality: tuple[object, ...]
    process: Process
    state: dict[str, int]
    counts: dict[str, int]


class ProductionPlanner:
    """Construit des lots generiques par expansion inverse des dependances.

    Le planificateur ne connait aucun nom de ressource ou de processus. Il
    compare les producteurs d'apres les objectifs declares, conserve la
    ressource qui finance un cycle de production et tient compte des
    sous-produits dans son stock virtuel.
    """

    _MAX_EXPANSIONS = 100_000

    def __init__(self, config: Config):
        self.config = config
        self.targets = tuple(t for t in (config.optimize or []) if t != "time")
        self._producers: dict[str, list[Process]] = defaultdict(list)
        for process in config.processes.values():
            for resource, quantity in process.results.items():
                if quantity > 0:
                    self._producers[resource].append(process)
        self.terminal = self._terminal_converter()
        self.goal = (
            next(iter(self.terminal.needs))
            if self.terminal is not None
            else (self.targets[0] if self.targets else None)
        )

    @property
    def enabled(self) -> bool:
        """Indique si un objectif metier exploitable est disponible."""

        return self.goal is not None

    def _terminal_converter(self) -> Process | None:
        """Detecte un convertisseur final instantane a une seule entree."""

        if len(self.targets) != 1:
            return None
        target = self.targets[0]
        candidates = self._producers.get(target, [])
        if len(candidates) != 1:
            return None
        process = candidates[0]
        if process.delay != 0 or len(process.needs) != 1:
            return None
        source = next(iter(process.needs))
        if source == target or process.results.get(source, 0) > 0:
            return None
        if not self._producers.get(source):
            return None
        return process

    def terminal_count(self, stocks: dict[str, int]) -> int:
        """Retourne le nombre maximal de conversions finales immediates."""

        if self.terminal is None:
            return 0
        return min(
            stocks.get(resource, 0) // quantity
            for resource, quantity in self.terminal.needs.items()
        )

    def build_batch(self, stocks: dict[str, int]) -> BatchPlan | None:
        """Choisit le meilleur producteur et construit ses dependances."""

        if self.goal is None:
            return None
        candidates: list[_BatchCandidate] = []
        for process in self._producers.get(self.goal, []):
            candidate = self._build_candidate(process, stocks)
            if candidate is not None:
                candidates.append(candidate)
        best = self._select_candidate(candidates)
        if best is None:
            return None
        self._extend_finite_batch(best.process, stocks, best.state, best.counts)
        return BatchPlan(
            counts=best.counts,
            expected_gain=self._gain(stocks, best.state),
        )

    def _build_candidate(
        self,
        process: Process,
        stocks: dict[str, int],
    ) -> _BatchCandidate | None:
        """Construit et évalue un candidat de production."""

        state = stocks.copy()
        counts: dict[str, int] = {}
        if not self._plan_process(process, state, counts, set(), [0]):
            return None
        gain = self._gain(stocks, state)
        if not gain or gain[0] <= 0:
            return None
        material_cost = self._material_cost(counts)
        duration = self._batch_duration(counts)
        quality = self._candidate_quality(gain, material_cost, duration)
        return _BatchCandidate(quality, process, state, counts)

    def _material_cost(self, counts: dict[str, int]) -> int:
        """Calcule le coût des ressources réellement consommées."""

        return sum(
            quantity * count
            for name, count in counts.items()
            for resource, quantity in self.config.processes[name].needs.items()
            if self.config.processes[name].results.get(resource, 0) < quantity
        )

    def _batch_duration(self, counts: dict[str, int]) -> int:
        """Calcule la durée cumulée d'un lot candidat."""

        return sum(
            self.config.processes[name].delay * count for name, count in counts.items()
        )

    def _candidate_quality(
        self,
        gain: tuple[int, ...],
        material_cost: int,
        duration: int,
    ) -> tuple[object, ...]:
        """Construit la clé de comparaison adaptée à l'objectif."""

        if self.config.optimize and self.config.optimize[0] == "time":
            return (-duration, gain, -material_cost)
        return (gain, -material_cost, -duration)

    def _select_candidate(
        self,
        candidates: list[_BatchCandidate],
    ) -> _BatchCandidate | None:
        """Sélectionne la meilleure qualité, puis le nom le plus petit."""

        if not candidates:
            return None
        best_quality = max(candidate.quality for candidate in candidates)
        return min(
            (
                candidate
                for candidate in candidates
                if candidate.quality == best_quality
            ),
            key=lambda candidate: candidate.process.name,
        )

    def _extend_finite_batch(
        self,
        process: Process,
        initial: dict[str, int],
        state: dict[str, int],
        counts: dict[str, int],
    ) -> None:
        """Regroupe les repetitions financees par un stock non renouvelable."""

        if self.goal is None or any(
            self.config.processes[name].needs.get(self.goal, 0) > 0 for name in counts
        ):
            return
        draining = any(
            state.get(resource, 0) < quantity
            for resource, quantity in initial.items()
            if resource != self.goal
        )
        if not draining:
            return
        expansions = [sum(counts.values())]
        while expansions[0] < self._MAX_EXPANSIONS:
            trial_state = state.copy()
            trial_counts = counts.copy()
            if not self._plan_process(
                process, trial_state, trial_counts, set(), expansions
            ):
                break
            state.clear()
            state.update(trial_state)
            counts.clear()
            counts.update(trial_counts)

    def _gain(self, before: dict[str, int], after: dict[str, int]) -> tuple[int, ...]:
        """Calcule le gain lexicographique d'un plan candidat."""

        resources = (
            (next(iter(self.terminal.needs)),)
            if self.terminal is not None
            else self.targets
        )
        return tuple(after.get(name, 0) - before.get(name, 0) for name in resources)

    def _ranked_producers(self, resource: str) -> list[Process]:
        """Classe les producteurs intermediaires sans hypothese de domaine."""

        return sorted(
            self._producers.get(resource, []),
            key=lambda process: (
                -(process.results.get(resource, 0) - process.needs.get(resource, 0)),
                -process.results.get(resource, 0),
                process.delay,
                sum(process.needs.values()),
                process.name,
            ),
        )

    def _ensure(
        self,
        resource: str,
        quantity: int,
        state: dict[str, int],
        counts: dict[str, int],
        visiting: set[str],
        expansions: list[int],
    ) -> bool:
        """Produit virtuellement une quantite, avec retour arriere local."""

        if state.get(resource, 0) >= quantity:
            return True
        if resource == self.goal or resource in visiting:
            return False
        while state.get(resource, 0) < quantity:
            before = state.get(resource, 0)
            progressed = False
            for producer in self._ranked_producers(resource):
                trial_state = state.copy()
                trial_counts = counts.copy()
                if not self._plan_process(
                    producer,
                    trial_state,
                    trial_counts,
                    visiting | {resource},
                    expansions,
                ):
                    continue
                if trial_state.get(resource, 0) <= before:
                    continue
                state.clear()
                state.update(trial_state)
                counts.clear()
                counts.update(trial_counts)
                progressed = True
                break
            if not progressed:
                return False
        return True

    def _plan_process(
        self,
        process: Process,
        state: dict[str, int],
        counts: dict[str, int],
        visiting: set[str],
        expansions: list[int],
    ) -> bool:
        """Ajoute une execution et toutes ses dependances au plan virtuel."""

        expansions[0] += 1
        if expansions[0] > self._MAX_EXPANSIONS:
            return False
        for resource, quantity in process.needs.items():
            if not self._ensure(
                resource, quantity, state, counts, visiting, expansions
            ):
                return False
        for resource, quantity in process.needs.items():
            state[resource] = state.get(resource, 0) - quantity
        for resource, quantity in process.results.items():
            state[resource] = state.get(resource, 0) + quantity
        counts[process.name] = counts.get(process.name, 0) + 1
        return True


def _target_requirements(config: Config) -> dict[str, dict[str, int]]:
    """Find unique producers for non-time optimization targets."""
    requirements: dict[str, dict[str, int]] = {}
    for target in config.optimize or []:
        if target == "time":
            continue
        producers = [
            proc
            for proc in config.processes.values()
            if proc.results.get(target, 0) > 0
        ]
        if len(producers) == 1:
            requirements[target] = producers[0].needs
    return requirements


def _sort_key_factory(
    config: Config,
    target_requirements: dict[str, dict[str, int]],
) -> Callable[[Process], tuple[int | str, ...]]:
    """Create the deterministic multi-criteria sort key."""
    analysis_logger = get_active_analysis_logger()

    def sort_key(proc: Process) -> tuple[int | str, ...]:
        key: list[int | str] = []
        for target in config.optimize or []:
            if target == "time":
                key.append(proc.delay)
                continue
            component_score = sum(
                target_requirements.get(target, {}).get(resource, 0) * qty
                for resource, qty in proc.results.items()
            )
            key.extend(
                (
                    -proc.results.get(target, 0),
                    -component_score,
                    sum(proc.needs.values()),
                )
            )
        key.append(proc.name)
        analysis_logger.log_key_value(
            "SORT_KEY_RESULT",
            {
                "process_name": proc.name,
                "delay": proc.delay,
                "needs": proc.needs,
                "results": proc.results,
                "key": tuple(key),
            },
            scope="optimizer.order_processes.sort_key",
        )
        return tuple(key)

    return sort_key


# Pour isoler order_processes et faciliter son evolution sous tests.
def order_processes(config: Config) -> list[Process]:
    """Retourne les processus tries selon ``config.optimize``.

    Parameters:
        config: Configuration complete deja parsee et validee.

    Returns:
        Liste de processus ordonnee de maniere deterministe.

    Raises:
        Aucune exception n'est levee explicitement.

    Contrat:
        A criteres equivalents, l'ordre alphabétique des noms doit rester
        stable pour eviter des traces non deterministes.
    """
    # Pour obtenir le logger d'analyse partage avec la couche CLI.
    analysis_logger = get_active_analysis_logger()
    # Pour etiqueter clairement les logs emis par ce module.
    order_scope = "optimizer.order_processes"
    # Pour exposer les donnees d'entree du tri avant toute transformation.
    analysis_logger.log_step(
        "ORDER_PROCESSES_START",
        {
            "optimize": config.optimize or [],
            "process_names": list(config.processes),
        },
        scope=order_scope,
    )

    target_requirements = _target_requirements(config)
    sort_key = _sort_key_factory(config, target_requirements)

    # Pour calculer un ordre deterministic selon les regles d'optimisation.
    ordered = sorted(config.processes.values(), key=sort_key)
    # Pour exposer le resultat final produit par ce module.
    analysis_logger.log_key_value(
        "ORDERED_PROCESS_NAMES",
        [proc.name for proc in ordered],
        scope=order_scope,
    )
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return ordered
