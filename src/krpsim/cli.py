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

from logger.analysis_log_krpsim import AnalysisLogger, set_active_analysis_logger

# Pour limiter le couplage aux composants internes necessaires.
from . import parser as parser_mod

# Pour limiter le couplage aux composants internes necessaires.
from .display import print_header, save_trace

# Pour limiter le couplage aux composants internes necessaires.
from .parser import ParseError

# Pour limiter le couplage aux composants internes necessaires.
from .simulator import Simulator


def _serialize_simulator_state(sim: Simulator) -> dict[str, object]:
    """Retourne un snapshot complet et lisible de l'etat du simulateur."""
    return {
        "config": {
            "stocks": sim.config.stocks,
            "processes": {
                name: {
                    "name": process.name,
                    "needs": process.needs,
                    "results": process.results,
                    "delay": process.delay,
                }
                for name, process in sim.config.processes.items()
            },
            "optimize": sim.config.optimize,
        },
        "stocks": sim.stocks,
        "time": sim.time,
        "_running": [
            {
                "process": {
                    "name": rp.process.name,
                    "needs": rp.process.needs,
                    "results": rp.process.results,
                    "delay": rp.process.delay,
                },
                "remaining": rp.remaining,
            }
            for rp in sim._running
        ],
        "trace": sim.trace,
        "deadlock": sim.deadlock,
        "_max_time": sim._max_time,
    }


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
    # Pour activer une vue d'analyse detaillee sans toucher aux logs standards.
    parser.add_argument(
        "--analysis-log",
        action="store_true",
        help="print detailed analysis logs for CLI pipeline and simulation",
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
def _validate_args(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
    analysis_logger: AnalysisLogger,
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
    # Pour etiqueter clairement les logs emis par cette fonction.
    scope = "_validate_args"
    # Pour manipuler un chemin canonique independant de l'OS.
    config_path = Path(args.config)
    # Pour tracer les preconditions de validation de maniere deterministe.
    analysis_logger.log_header("INPUT VALIDATION", scope=scope)
    # Pour exposer la cible exacte controlee par la validation.
    analysis_logger.log_key_value("CONFIG_PATH", str(config_path), scope=scope)
    # Pour exposer la borne de simulation demandee par l'utilisateur.
    analysis_logger.log_key_value("REQUESTED_DELAY", args.delay, scope=scope)
    # Pour bloquer la traversal de chemin hors perimetre attendu.
    has_path_traversal = ".." in config_path.parts
    # Pour rendre explicite le resultat du premier garde-fou.
    analysis_logger.log_key_value(
        "HAS_PATH_TRAVERSAL",
        has_path_traversal,
        scope=scope,
    )
    if has_path_traversal:
        # Pour fournir une erreur CLI uniforme et immediate a l'utilisateur.
        parser.error("path traversal detected in config path")
    # Pour echouer tot quand la cible n'est pas un fichier valide.
    is_file = config_path.is_file()
    # Pour documenter la verification d'existence avant lecture.
    analysis_logger.log_key_value("CONFIG_FILE_EXISTS", is_file, scope=scope)
    if not is_file:
        # Pour fournir une erreur CLI uniforme et immediate a l'utilisateur.
        parser.error(f"invalid config path: '{args.config}'")
    # Pour detecter un probleme de permission avant l'execution metier.
    is_readable = os.access(config_path, os.R_OK)
    # Pour tracer explicitement l'etat d'acces lu par la CLI.

    if not is_readable:
        # Pour fournir une erreur CLI uniforme et immediate a l'utilisateur.
        parser.error(f"config file is not readable: '{args.config}'")
    # Pour imposer une borne temporelle coherent avec le contrat CLI.
    positive_delay = args.delay > 0
    # Pour rendre visible le resultat du controle de borne temporelle.
    analysis_logger.log_key_value("DELAY_IS_POSITIVE", positive_delay, scope=scope)
    if not positive_delay:
        # Pour fournir une erreur CLI uniforme et immediate a l'utilisateur.
        parser.error("delay must be a positive integer")
    # Pour marquer la fin du bloc de validation dans le flux d'analyse.
    analysis_logger.log_step("VALIDATION_DONE", scope=scope)


# Pour isoler _run_simulation et faciliter son evolution sous tests.
def _run_simulation(
    args: argparse.Namespace,
    analysis_logger: AnalysisLogger,
) -> tuple[Simulator, bool]:
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
    # Pour etiqueter clairement les logs emis par cette fonction.
    scope = "_run_simulation"
    # Pour exposer clairement les phases metier executees par la CLI.
    analysis_logger.log_header("SIMULATION PIPELINE", scope=scope)
    # Pour tracer le point d'entree exact du parsing de configuration.
    analysis_logger.log_step("PARSING_CONFIG_FILE", args.config, scope=scope)
    # Pour reutiliser la validation canonique plutot qu'un parsing local.
    config = parser_mod.parse_file(Path(args.config))
    # Pour inspecter les donnees source qui pilotent l'orchestration.
    analysis_logger.log_key_value("INITIAL_STOCKS", config.stocks, scope=scope)
    # Pour afficher l'ordre de declaration des processus disponibles.
    analysis_logger.log_key_value(
        "PROCESS_NAMES",
        list(config.processes),
        scope=scope,
    )
    # Pour tracer les criteres d'optimisation bruts de la configuration.
    analysis_logger.log_key_value(
        "OPTIMIZATION_CRITERIA",
        config.optimize or [],
        scope=scope,
    )
    # Pour respecter l'exception de delai du mode optimize(time).
    ignore_delay = bool(config.optimize and config.optimize[0] == "time")
    # Pour expliquer le calcul du mode de borne temporelle.
    analysis_logger.log_calculation(
        "IGNORE_DELAY_MODE",
        [
            "ignore_delay = bool(config.optimize and config.optimize[0] == 'time')",
            f"config.optimize = {config.optimize or []}",
        ],
        ignore_delay,
        scope=scope,
    )
    # Pour indiquer explicitement le passage de controle au moteur de simulation.
    analysis_logger.log_step(
        "SIMULATOR_INIT_START",
        "calling Simulator(config)",
        scope=scope,
    )
    # Pour executer la logique metier via l'implementation de reference.
    sim = Simulator(config)
    # Pour exposer l'etat initial du moteur juste apres son initialisation.
    analysis_logger.log_key_value(
        "SIMULATOR_STATE_AFTER_INIT",
        _serialize_simulator_state(sim),
        scope=scope,
    )
    # Pour contextualiser l'execution avant la trace des cycles.
    print_header(config)
    # Pour imposer une borne finie meme en mode optimisation.
    run_delay = args.delay if not ignore_delay else 500
    # Pour expliciter la borne effectivement transmise au simulateur.
    analysis_logger.log_calculation(
        "RUN_DELAY",
        [
            "run_delay = args.delay if not ignore_delay else 500",
            f"args.delay = {args.delay}",
            f"ignore_delay = {ignore_delay}",
        ],
        run_delay,
        scope=scope,
    )
    # Pour indiquer explicitement le lancement du moteur de simulation.
    analysis_logger.log_step(
        "SIMULATOR_RUN_START",
        {"max_time": run_delay},
        scope=scope,
    )
    # Pour produire l'etat de reference a partir du moteur unique.
    trace = sim.run(run_delay)
    # Pour indiquer explicitement la fin du run moteur et son resume.
    analysis_logger.log_step(
        "SIMULATOR_RUN_DONE",
        {
            "sim_time": sim.time,
            "trace_len": len(trace),
            "deadlock": sim.deadlock,
        },
        scope=scope,
    )
    # Pour exposer l'etat complet du moteur a la fin du run.
    analysis_logger.log_key_value(
        "SIMULATOR_STATE_AFTER_RUN",
        _serialize_simulator_state(sim),
        scope=scope,
    )
    analysis_logger.log_key_value("TRACE_EVENT_COUNT", len(trace), scope=scope)
    # Pour exposer l'etat final du moteur apres execution.
    analysis_logger.log_key_value("SIM_TIME_AFTER_RUN", sim.time, scope=scope)
    # Pour exposer le drapeau de deadlock calcule par le moteur.
    analysis_logger.log_key_value("SIM_DEADLOCK", sim.deadlock, scope=scope)
    # Pour exposer l'etat de stock final avant affichage.
    analysis_logger.log_key_value("STOCKS_AFTER_RUN", sim.stocks, scope=scope)
    # Pour conserver l'ordre temporel lors de la sortie de trace.
    for cycle, name in trace:
        # Pour fournir un retour utilisateur directement lisible en CLI.
        print(f"{cycle}:{name}")
    # Pour persister une trace verifiable avant la fin du processus.
    analysis_logger.log_step("SAVING_TRACE_FILE", args.trace, scope=scope)
    save_trace(trace, Path(args.trace))
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return sim, ignore_delay


def _configure_logging(args: argparse.Namespace) -> None:
    """Configure CLI log sinks from parsed arguments."""
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if args.log:
        handlers.append(logging.FileHandler(args.log))
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(message)s",
        handlers=handlers,
        force=True,
    )


def _run_checked_simulation(
    args: argparse.Namespace, analysis_logger: AnalysisLogger
) -> tuple[Simulator, bool]:
    """Run the simulation and convert parse errors to the CLI contract."""
    try:
        return _run_simulation(args, analysis_logger)
    except ParseError as exc:
        analysis_logger.log_step("PARSE_ERROR", str(exc), scope="main")
        print(f"invalid config: {exc}")
        raise SystemExit(1) from exc


def _exit_code_for_simulation(
    sim: Simulator,
    requested_delay: int,
    ignore_delay: bool,
    analysis_logger: AnalysisLogger,
) -> int:
    """Log the simulation outcome and return its process exit code."""
    logger = logging.getLogger(__name__)
    scope = "main"
    analysis_logger.log_header("EXIT DECISION", scope=scope)
    analysis_logger.log_key_value("IGNORE_DELAY", ignore_delay, scope=scope)
    analysis_logger.log_key_value("SIM_TIME", sim.time, scope=scope)
    analysis_logger.log_key_value("REQUESTED_DELAY", requested_delay, scope=scope)
    analysis_logger.log_key_value("SIM_DEADLOCK", sim.deadlock, scope=scope)
    if not ignore_delay and sim.time >= requested_delay:
        limit = requested_delay if sim.time > requested_delay else sim.time
        logger.warning("Max time reached at time %d", limit)
        analysis_logger.log_step(
            "EXIT_REASON", f"max_time_reached(limit={limit})", scope=scope
        )
        return 1
    if sim.deadlock:
        logger.warning("Deadlock detected at time %d", sim.time)
        analysis_logger.log_step("EXIT_REASON", "deadlock", scope=scope)
        return 1
    logger.warning("No more process doable at time %d", sim.time)
    analysis_logger.log_step("EXIT_REASON", "no_more_process_doable", scope=scope)
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
    # Pour etiqueter clairement les logs emis par cette fonction.
    scope = "main"
    # Pour centraliser les traces d'analyse du comportement de la CLI.
    analysis_logger = AnalysisLogger(enabled=args.analysis_log)
    # Pour partager le logger d'analyse avec les sous-modules (ex: optimizer).
    set_active_analysis_logger(analysis_logger)
    # Pour exposer les arguments parsees dans un bloc d'entree unique.
    analysis_logger.log_header("CLI ENTRYPOINT", scope=scope)
    # Pour garder un format deterministe pour reproduire un run exact.
    analysis_logger.log_key_value("PARSED_ARGS", vars(args), scope=scope)

    _configure_logging(args)

    # Pour echouer tot avant toute operation couteuse ou irreversible.
    _validate_args(args, parser, analysis_logger)

    # Pour convertir une erreur bas niveau en diagnostic exploitable.
    sim, ignore_delay = _run_checked_simulation(args, analysis_logger)

    # Pour garder un canal de diagnostic coherent dans tout le module.
    exit_code = _exit_code_for_simulation(
        sim, args.delay, ignore_delay, analysis_logger
    )

    # Pour stabiliser l'ordre d'affichage des ressources finales.
    stock_names = sorted(sim.config.all_stock_names())
    # Pour aligner la sortie et faciliter la lecture des diffs.
    max_len = max((len(name) for name in stock_names), default=0)
    # Pour fournir un retour utilisateur directement lisible en CLI.
    print("Final Stocks:")
    # Pour fournir un snapshot stable des stocks finaux pour le diagnostic.
    analysis_logger.log_key_value(
        "FINAL_STOCKS",
        {name: sim.stocks.get(name, 0) for name in stock_names},
        scope=scope,
    )
    # Pour afficher les stocks dans un ordre deterministic.
    for name in stock_names:
        # Pour fournir un retour utilisateur directement lisible en CLI.
        print(f"  {name:<{max_len}}  => {sim.stocks.get(name, 0)}")

    # Pour tracer la valeur de sortie renvoyee au shell.
    analysis_logger.log_key_value("EXIT_CODE", exit_code, scope=scope)

    # Pour fournir au shell un code retour exploitable en automatisation.
    return exit_code


# Pour proteger un invariant de comparaison critique ici.
if __name__ == "__main__":
    # Pour signaler sans delai une violation explicite du contrat.
    raise SystemExit(main())
