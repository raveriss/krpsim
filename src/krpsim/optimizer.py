"""Strategie de tri des processus avant lancement en simulation.

Ce module isole la politique d'ordonnancement pour pouvoir faire evoluer
la priorisation sans diffuser des effets de bord dans le simulateur.
"""

# Pour retarder l'evaluation des types et limiter les cycles.
from __future__ import annotations

from collections.abc import Callable

from logger.analysis_log_krpsim import get_active_analysis_logger

# Pour limiter le couplage aux composants internes necessaires.
from .parser import Config, Process


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
