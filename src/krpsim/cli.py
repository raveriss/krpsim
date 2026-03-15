"""Interface en ligne de commande du simulateur krpsim.

Ce module porte le contrat d'entree/sortie du binaire ``krpsim`` et
stabilise les erreurs utilisateur, les traces machine et les codes retour.
"""

# Pour retarder l'evaluation des types et limiter les cycles.
from __future__ import annotations

# Pour stabiliser l'interface CLI et ses erreurs utilisateur.
import argparse
# Pour rendre le diagnostic activable sans polluer la sortie.
import logging
# Pour appliquer des verifications d'acces dependantes du systeme.
import os
# Pour aligner les flux CLI avec les attentes du shell.
import sys
# Pour eviter les chemins fragiles relies aux separateurs OS.
from pathlib import Path

# Pour limiter le couplage aux composants internes necessaires.
from . import parser as parser_mod
# Pour limiter le couplage aux composants internes necessaires.
from .display import format_trace, print_header, save_trace
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
    # Pour figer l'interface publique attendue par les scripts externes.
    parser.add_argument(
        # Pour stabiliser le message utilisateur expose par la CLI.
        "-v",
        # Pour stabiliser le message utilisateur expose par la CLI.
        "--verbose",
        # Pour garder une option booleenne simple a activer en CLI.
        action="store_true",
        # Pour rendre l'usage autonome sans lecture du code source.
        help="enable verbose logging",
    # Pour clore le bloc sans ambiguite de structure.
    )
    # Pour figer l'interface publique attendue par les scripts externes.
    parser.add_argument(
        # Pour stabiliser le message utilisateur expose par la CLI.
        "--log",
        # Pour rendre l'usage autonome sans lecture du code source.
        help="path to write logs to",
    # Pour clore le bloc sans ambiguite de structure.
    )
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return parser


# Pour isoler _validate_args et faciliter son evolution sous tests.
def _validate_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
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
    if ".." in config_path.parts:
        # Pour fournir une erreur CLI uniforme et immediate a l'utilisateur.
        parser.error("path traversal detected in config path")
    # Pour echouer tot quand la cible n'est pas un fichier valide.
    if not config_path.is_file():
        # Pour fournir une erreur CLI uniforme et immediate a l'utilisateur.
        parser.error(f"invalid config path: '{args.config}'")
    # Pour detecter un probleme de permission avant l'execution metier.
    if not os.access(config_path, os.R_OK):
        # Pour fournir une erreur CLI uniforme et immediate a l'utilisateur.
        parser.error(f"config file is not readable: '{args.config}'")
    # Pour imposer une borne temporelle coherent avec le contrat CLI.
    if args.delay <= 0:
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
    run_delay = args.delay if not ignore_delay else 10_000
    # Pour produire l'etat de reference a partir du moteur unique.
    trace = sim.run(run_delay)
    # Pour conserver l'ordre temporel lors de la sortie de trace.
    for line in format_trace(trace):
        # Pour fournir un retour utilisateur directement lisible en CLI.
        print(line)
    # Pour persister une trace verifiable avant la fin du processus.
    save_trace(trace, Path(args.trace))
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return sim, ignore_delay


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

    # Pour centraliser les sorties de logs sans multiplier la configuration.
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    # Pour n'ouvrir un fichier de log que sur demande explicite.
    if args.log:
        # Pour conserver une trace persistante utile en CI et support.
        handlers.append(logging.FileHandler(args.log))
    # Pour imposer un format de logs stable entre execution et tests.
    logging.basicConfig(
        # Pour activer le detail seulement sur demande explicite.
        level=logging.INFO if args.verbose else logging.WARNING,
        # Pour garder des logs sobres et diffables en automatisation.
        format="%(message)s",
        # Pour centraliser tous les sinks de logs dans une seule config.
        handlers=handlers,
        # Pour eviter l'empilement de handlers lors des appels repetes.
        force=True,
    # Pour clore le bloc sans ambiguite de structure.
    )

    # Pour echouer tot avant toute operation couteuse ou irreversible.
    _validate_args(args, parser)

    # Pour convertir une erreur bas niveau en diagnostic exploitable.
    try:
        # Pour separer clairement execution metier et gestion du code retour.
        sim, ignore_delay = _run_simulation(args)
    # Pour traduire un echec technique en message stable pour l'appelant.
    except ParseError as exc:
        # Pour fournir un retour utilisateur directement lisible en CLI.
        print(f"invalid config: {exc}")
        # Pour signaler sans delai une violation explicite du contrat.
        raise SystemExit(1)

    # Pour garder un canal de diagnostic coherent dans tout le module.
    logger = logging.getLogger(__name__)
    # Pour centraliser le statut final sans sorties anticipees.
    exit_code = 0
    # Pour traiter explicitement un cas d'entree invalide ou absent.
    if not ignore_delay and sim.time >= args.delay:
        # Pour afficher une borne coherente meme en cas de depassement.
        limit = args.delay if sim.time > args.delay else sim.time
        # Pour distinguer les terminaisons anormales dans les diagnostics.
        logger.warning("Max time reached at time %d", limit)
        # Pour centraliser le statut final sans sorties anticipees.
        exit_code = 1
    # Pour maintenir un ordre de priorite stable entre cas exclusifs.
    elif sim.deadlock:
        # Pour distinguer les terminaisons anormales dans les diagnostics.
        logger.warning("Deadlock detected at time %d", sim.time)
        # Pour centraliser le statut final sans sorties anticipees.
        exit_code = 1
    # Pour couvrir explicitement le cas complementaire du contrat.
    else:
        # Pour distinguer les terminaisons anormales dans les diagnostics.
        logger.warning("No more process doable at time %d", sim.time)

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
