"""Strategie de tri des processus avant lancement en simulation.

Ce module isole la politique d'ordonnancement pour pouvoir faire evoluer
la priorisation sans diffuser des effets de bord dans le simulateur.
"""

# Pour retarder l'evaluation des types et limiter les cycles.
from __future__ import annotations

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
        # Pour garantir un tie-break deterministic a score equivalent.
        key.append(proc.name)
        # Pour rendre a l'appelant le resultat promis par le contrat.
        return tuple(key)

    # Pour rendre a l'appelant le resultat promis par le contrat.
    return sorted(config.processes.values(), key=sort_key)
