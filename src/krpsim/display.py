"""Utilitaires d'affichage pour sortie humaine et trace machine.

Ce module isole la presentation pour conserver un format stable, reutilisable
par la CLI et verifiable par les tests.
"""

# Pour retarder l'evaluation des types et limiter les cycles.
from __future__ import annotations

# Pour rendre le diagnostic activable sans polluer la sortie.
import logging
# Pour appliquer des verifications d'acces dependantes du systeme.
import os
# Pour eviter les chemins fragiles relies aux separateurs OS.
from pathlib import Path
# Pour garder des signatures stables sur les objets iterables.
from typing import Iterable

# Pour limiter le couplage aux composants internes necessaires.
from .parser import Config

# Pour traiter les cas de pluriel irregulier sans logique complexe.
_IRREGULAR_PLURALS: dict[str, str] = {"process": "processes"}


# Pour isoler _pluralize et faciliter son evolution sous tests.
def _pluralize(word: str, count: int) -> str:
    """Retourne une forme singulier/pluriel stable pour l'affichage.

    Parameters:
        word: Mot a adapter au contexte numerique.
        count: Quantite associee au mot.

    Returns:
        Le mot au singulier si ``count == 1`` sinon une forme plurielle.

    Raises:
        Aucune exception n'est levee explicitement.

    Contrat:
        Les termes de sortie doivent rester cohérents d'une execution a
        l'autre pour conserver la lisibilite des logs.
    """
    # Pour proteger un invariant de comparaison critique ici.
    if count == 1:
        # Pour rendre a l'appelant le resultat promis par le contrat.
        return word
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return _IRREGULAR_PLURALS.get(word, word + "s")


# Pour isoler print_header et faciliter son evolution sous tests.
def print_header(config: Config) -> None:
    """Affiche le resume initial d'une configuration.

    Parameters:
        config: Configuration parsee transmise au simulateur.

    Returns:
        ``None``.

    Raises:
        Aucune exception n'est levee explicitement.

    Contrat:
        Le header doit rester deterministic pour etre diffable en CI.
    """
    # Pour exclure le critere temps du comptage metier affiche.
    optimize_count = len([o for o in (config.optimize or []) if o != "time"])
    # Pour preparer un fragment de sortie reutilisable et coherent.
    process_info = (
        # Pour conserver une phrase naturelle sans logique de pluralisation
        # dupliquee.
        f"{len(config.processes)} {_pluralize('process', len(config.processes))}"
    # Pour clore le bloc sans ambiguite de structure.
    )
    # Pour calculer un total unique avant composition du message.
    stock_count = len(config.all_stock_names())
    # Pour garder un message stock coherent avec la pluralisation.
    stock_info = f"{stock_count} {_pluralize('stock', stock_count)}"
    # Pour rendre visible le nombre de cibles metier optimisees.
    objective_info = f"{optimize_count} to optimize"
    # Pour fournir un retour utilisateur directement lisible en CLI.
    print("Nice file! " f"{process_info}, {stock_info}, {objective_info}")
    # Pour fournir un retour utilisateur directement lisible en CLI.
    print("Evaluating ... done.")
    # Pour fournir un retour utilisateur directement lisible en CLI.
    print("Main walk:")
    # Pour appliquer la logique specifique au mode optimisation.
    if config.optimize:
        # Pour fournir un retour utilisateur directement lisible en CLI.
        print(f"Optimization criteria: {', '.join(config.optimize)}")


# Pour isoler format_trace et faciliter son evolution sous tests.
def format_trace(trace: Iterable[tuple[int, str]]) -> list[str]:
    """Convertit une trace interne vers le format ``cycle:process``.

    Parameters:
        trace: Evenements bruts issus du simulateur.

    Returns:
        Une liste de lignes prêtes a afficher ou ecrire.

    Raises:
        Aucune exception n'est levee explicitement.

    Contrat:
        Le format textuel doit rester identique pour la verification
        ulterieure via ``krpsim_verif``.
    """
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return [f"{cycle}:{name}" for cycle, name in trace]


# Pour marquer explicitement une trace vide mais valide.
EMPTY_TRACE_MSG = "# no process executed (optimization)"


# Pour isoler save_trace et faciliter son evolution sous tests.
def save_trace(trace: Iterable[tuple[int, str]], path: Path) -> None:
    """Ecrit la trace machine sur disque avec persistance forte.

    Parameters:
        trace: Trace en memoire issue de la simulation.
        path: Fichier cible a ecrire.

    Returns:
        ``None``.

    Raises:
        OSError:
            Si l'ecriture ou la synchronisation disque echoue.

    Contrat:
        Le fichier doit representer un etat durable avant retour de fonction.
    """
    # Pour reutiliser un format unique entre affichage et persistance.
    lines = format_trace(trace)
    # Pour distinguer une execution vide d'une sortie absente.
    if not lines:
        # Pour differencier une trace vide valide d'un fichier corrompu.
        lines.append(EMPTY_TRACE_MSG)
    # Pour garantir la fermeture de ressource meme en cas d'erreur.
    with path.open("w", encoding="utf-8") as fh:
        # Pour valider chaque ligne avec le meme niveau d'exigence.
        for line in lines:
            # Pour garantir une trace lisible ligne par ligne par le
            # verificateur.
            fh.write(line + "\n")
        # Pour vider le buffer Python avant synchronisation disque.
        fh.flush()
        # Pour reduire le risque de perte en cas d'arret brutal.
        os.fsync(fh.fileno())
    # Pour conserver un point d'audit sur le chemin de sortie reel.
    logging.getLogger(__name__).info("trace saved to %s", path)
