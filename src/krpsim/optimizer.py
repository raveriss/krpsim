"""Strategie de tri des processus avant lancement en simulation.

Ce module isole la politique d'ordonnancement pour pouvoir faire evoluer
la priorisation sans diffuser des effets de bord dans le simulateur.
"""

# Pour retarder l'evaluation des types et limiter les cycles.
from __future__ import annotations

from logger.analysis_log_krpsim import get_active_analysis_logger

# Pour limiter le couplage aux composants internes necessaires.
from .parser import Config, Process


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
    # Pour etiqueter clairement les logs de la cle de tri interne.
    key_scope = "optimizer.order_processes.sort_key"
    # Pour exposer les donnees d'entree du tri avant toute transformation.
    analysis_logger.log_step(
        "ORDER_PROCESSES_START",
        {
            "optimize": config.optimize or [],
            "process_names": list(config.processes),
        },
        scope=order_scope,
    )

    # Pour donner un signal de priorite aux producteurs de composants qui
    # permettent ensuite de fabriquer une cible optimisee.
    target_requirements: dict[str, dict[str, int]] = {}
    if config.optimize:
        for target in config.optimize:
            if target == "time":
                continue
            producers = [
                proc
                for proc in config.processes.values()
                if proc.results.get(target, 0) > 0
            ]
            if len(producers) == 1:
                target_requirements[target] = producers[0].needs

    def need_cost(proc: Process) -> int:
        """Retourne le cout total des ressources consommees."""
        return sum(proc.needs.values())

    # Pour isoler sort_key et faciliter son evolution sous tests.
    def sort_key(proc: Process) -> tuple[int | str, ...]:
        """Construit une cle de tri multi-criteres deterministic.

        Parameters:
            proc: Processus dont on calcule la priorite.

        Returns:
            Tuple ordonnable utilise par ``sorted``.

        Raises:
            Aucune exception n'est levee explicitement.

        Contrat:
            Chaque critere ajoute dans ``optimize`` doit influencer
            l'ordre de facon previsible et reproducible.
        """
        # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
        key: list[int | str] = []
        # Pour appliquer la logique specifique au mode optimisation.
        if config.optimize:
            # Pour appliquer uniformement la regle a chaque element concerne.
            for target in config.optimize:
                # Pour proteger un invariant de comparaison critique ici.
                if target == "time":
                    # Pour prioriser les processus les plus courts.
                    # Ce choix suit le critere optimize(time).
                    key.append(proc.delay)
                # Pour couvrir explicitement le cas complementaire du contrat.
                else:
                    # Pour inverser le tri et favoriser les plus gros
                    # producteurs sur la cible courante.
                    key.append(-proc.results.get(target, 0))
                    component_score = sum(
                        target_requirements.get(target, {}).get(resource, 0) * qty
                        for resource, qty in proc.results.items()
                    )
                    key.append(-component_score)
                    key.append(need_cost(proc))
        # Pour garantir un tie-break deterministic a score equivalent.
        key.append(proc.name)
        # Pour rendre visible la cle calculee pour chaque processus.
        analysis_logger.log_key_value(
            "SORT_KEY_RESULT",
            {
                "process_name": proc.name,
                "delay": proc.delay,
                "needs": proc.needs,
                "results": proc.results,
                "key": tuple(key),
            },
            scope=key_scope,
        )
        # Pour rendre a l'appelant le resultat promis par le contrat.
        return tuple(key)

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
