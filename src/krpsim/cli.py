"""Interface en ligne de commande du simulateur krpsim.

Ce module porte le contrat d'entree/sortie du binaire ``krpsim`` et
stabilise les erreurs utilisateur, les traces machine et les codes retour.
"""

# Pour retarder l'evaluation des types et limiter les cycles.
from __future__ import annotations

# Pour stabiliser l'interface CLI et ses erreurs utilisateur.
import argparse

# Pour appliquer des verifications d'acces dependantes du systeme.
import os

# Pour eviter les chemins fragiles relies aux separateurs OS.
from pathlib import Path

# Pour limiter le couplage aux composants internes necessaires.
from . import parser as parser_mod

# Pour limiter le couplage aux composants internes necessaires.
from .display import print_header, save_trace

# Pour limiter le couplage aux composants internes necessaires.
from .parser import ParseError

# Pour limiter le couplage aux composants internes necessaires.
from .simulator import Simulator


# Pour isoler build_parser et faciliter son evolution sous tests.
def build_parser() -> argparse.ArgumentParser:
    """Construit le parseur CLI expose au binaire ``krpsim``.

    Parameters:
        Aucun parametre.

    Returns:
        Un parseur ``argparse`` configure avec le contrat public.

    Raises:
        Aucune exception n'est levee explicitement par cette fonction.

    Contrat:
        La forme des options doit rester stable pour garantir la
        compatibilite des scripts d'automatisation.
    """
    # Pour declarer un contrat CLI explicite et versionnable.
    parser = argparse.ArgumentParser(prog="krpsim")
    # Pour figer l'interface publique attendue par les scripts externes.
    parser.add_argument("config", help="configuration file path")
    # Pour figer l'interface publique attendue par les scripts externes.
    parser.add_argument(
        # Pour stabiliser le message utilisateur expose par la CLI.
        "delay",
        # Pour imposer un type numerique des la lecture des arguments.
        type=int,
        # Pour rendre l'usage autonome sans lecture du code source.
        help=(
            # Pour stabiliser le message utilisateur expose par la CLI.
            "maximum delay allowed (inclusive upper bound, cycles run while "
            # Pour stabiliser le message utilisateur expose par la CLI.
            "time <= delay)"
            # Pour clore le bloc sans ambiguite de structure.
        ),
        # Pour clore le bloc sans ambiguite de structure.
    )
    # Pour figer l'interface publique attendue par les scripts externes.
    parser.add_argument(
        # Pour stabiliser le message utilisateur expose par la CLI.
        "--trace",
        # Pour fournir un comportement predictible sans option explicite.
        default="trace.txt",
        # Pour rendre l'usage autonome sans lecture du code source.
        help="path of the file to write machine trace to",
        # Pour clore le bloc sans ambiguite de structure.
    )
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return parser


# Pour isoler _validate_args et faciliter son evolution sous tests.
def _validate_args(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> None:
    """Valide les arguments CLI avant toute simulation.

    Parameters:
        args: Arguments resolves par ``argparse``.
        parser: Parseur utilise pour emettre des erreurs uniformes.

    Returns:
        ``None``.

    Raises:
        SystemExit:
            Leve indirectement via ``parser.error`` si une contrainte
            d'entree n'est pas satisfaite.

    Contrat:
        Toute entree invalide doit etre rejetee avant d'ouvrir des fichiers
        ou de lancer la simulation.
    """
    # Pour manipuler un chemin canonique independant de l'OS.
    config_path = Path(args.config)
    # Pour bloquer la traversal de chemin hors perimetre attendu.
    has_path_traversal = ".." in config_path.parts
    if has_path_traversal:
        # Pour fournir une erreur CLI uniforme et immediate a l'utilisateur.
        parser.error("path traversal detected in config path")
    # Pour echouer tot quand la cible n'est pas un fichier valide.
    is_file = config_path.is_file()
    if not is_file:
        # Pour fournir une erreur CLI uniforme et immediate a l'utilisateur.
        parser.error(f"invalid config path: '{args.config}'")
    # Pour detecter un probleme de permission avant l'execution metier.
    is_readable = os.access(config_path, os.R_OK)

    if not is_readable:
        # Pour fournir une erreur CLI uniforme et immediate a l'utilisateur.
        parser.error(f"config file is not readable: '{args.config}'")
    # Pour imposer une borne temporelle coherent avec le contrat CLI.
    positive_delay = args.delay > 0
    if not positive_delay:
        # Pour fournir une erreur CLI uniforme et immediate a l'utilisateur.
        parser.error("delay must be a positive integer")


# Pour isoler _run_simulation et faciliter son evolution sous tests.
def _run_simulation(args: argparse.Namespace) -> tuple[Simulator, bool]:
    """Execute la simulation et persiste la trace machine.

    Parameters:
        args: Arguments valides fournis par la CLI.

    Returns:
        Un tuple ``(simulateur, ignore_delay)`` permettant a ``main`` de
        calculer le code retour selon le mode d'optimisation.

    Raises:
        ParseError:
            Propagee si le fichier de configuration est invalide.

    Contrat:
        La trace affichee a l'ecran et celle ecrite sur disque doivent
        representer exactement la meme execution.
    """
    # Pour reutiliser la validation canonique plutot qu'un parsing local.
    config = parser_mod.parse_file(Path(args.config))
    # Pour respecter l'exception de delai du mode optimize(time).
    ignore_delay = bool(config.optimize and config.optimize[0] == "time")
    # Pour executer la logique metier via l'implementation de reference.
    sim = Simulator(config)
    # Pour contextualiser l'execution avant la trace des cycles.
    print_header(config)
    # Pour imposer une borne finie meme en mode optimisation.
    run_delay = args.delay if not ignore_delay else 500
    # Pour produire l'etat de reference a partir du moteur unique.
    trace = sim.run(run_delay)
    # Pour conserver l'ordre temporel lors de la sortie de trace.
    for cycle, name in trace:
        # Pour fournir un retour utilisateur directement lisible en CLI.
        print(f"{cycle}:{name}")
    save_trace(trace, Path(args.trace))
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return sim, ignore_delay


def _run_checked_simulation(args: argparse.Namespace) -> tuple[Simulator, bool]:
    """Run the simulation and convert parse errors to the CLI contract."""
    try:
        return _run_simulation(args)
    except ParseError as exc:
        print(f"invalid config: {exc}")
        raise SystemExit(1) from exc


def _exit_code_for_simulation(
    sim: Simulator,
    requested_delay: int,
    ignore_delay: bool,
) -> int:
    """Print the simulation outcome and return its process exit code."""
    if not ignore_delay and sim.time >= requested_delay:
        limit = requested_delay if sim.time > requested_delay else sim.time
        print(f"Max time reached at time {limit}")
        return 1
    if sim.deadlock:
        print(f"Deadlock detected at time {sim.time}")
        return 1
    print(f"No more process doable at time {sim.time}")
    return 0


# Pour isoler main et faciliter son evolution sous tests.
def main(argv: list[str] | None = None) -> int:
    """Point d'entree principal du binaire ``krpsim``.

    Parameters:
        argv: Liste d'arguments optionnelle pour tests et appels internes.

    Returns:
        ``0`` si la simulation termine sans limite atteinte ni deadlock,
        ``1`` sinon.

    Raises:
        SystemExit:
            Levee explicitement si la configuration ne peut pas etre parsee.

    Contrat:
        Le code retour doit rester fiable pour les pipelines CI/CD.
    """
    # Pour conserver un point unique de configuration des arguments.
    parser = build_parser()
    # Pour permettre l'injection d'arguments en test unitaire.
    args = parser.parse_args(argv)

    # Pour echouer tot avant toute operation couteuse ou irreversible.
    _validate_args(args, parser)

    # Pour convertir une erreur bas niveau en diagnostic exploitable.
    sim, ignore_delay = _run_checked_simulation(args)

    # Pour garder un canal de diagnostic coherent dans tout le module.
    exit_code = _exit_code_for_simulation(sim, args.delay, ignore_delay)

    # Pour stabiliser l'ordre d'affichage des ressources finales.
    stock_names = sorted(sim.config.all_stock_names())
    # Pour aligner la sortie et faciliter la lecture des diffs.
    max_len = max((len(name) for name in stock_names), default=0)
    # Pour fournir un retour utilisateur directement lisible en CLI.
    print("Final Stocks:")
    # Pour afficher les stocks dans un ordre deterministic.
    for name in stock_names:
        # Pour fournir un retour utilisateur directement lisible en CLI.
        print(f"  {name:<{max_len}}  => {sim.stocks.get(name, 0)}")

    # Pour fournir au shell un code retour exploitable en automatisation.
    return exit_code


# Pour proteger un invariant de comparaison critique ici.
if __name__ == "__main__":
    # Pour signaler sans delai une violation explicite du contrat.
    raise SystemExit(main())
