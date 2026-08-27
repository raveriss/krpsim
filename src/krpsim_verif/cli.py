"""Interface CLI du verificateur de trace ``krpsim_verif``.

Ce module valide une trace produite par le simulateur et expose des codes
retour stables pour les chaines d'automatisation.
"""

# Pour retarder l'evaluation des types et limiter les cycles.
from __future__ import annotations

# Pour stabiliser l'interface CLI et ses erreurs utilisateur.
import argparse

# Pour rendre le diagnostic activable sans polluer la sortie.
import logging

# Pour eviter les chemins fragiles relies aux separateurs OS.
from pathlib import Path

# Pour reutiliser la logique canonique du simulateur sans duplication.
from krpsim.parser import ParseError
from krpsim.simulator import Simulator
from logger.analysis_log_krpsim import (
    set_active_analysis_logger as set_krpsim_analysis_logger,
)

# Pour centraliser les traces d'analyse du verificateur.
from logger.analysis_log_krpsim_verif import AnalysisLogger, set_active_analysis_logger

# Pour limiter le couplage aux composants internes necessaires.
from .verifier import TraceError, verify_files


# Pour isoler build_parser et faciliter son evolution sous tests.
def build_parser() -> argparse.ArgumentParser:
    """Construit le parseur CLI du verificateur.

    Parameters:
        Aucun parametre.

    Returns:
        Parseur ``argparse`` avec le contrat public de ``krpsim_verif``.

    Raises:
        Aucune exception n'est levee explicitement.

    Contrat:
        Les options exposees doivent rester stables pour les scripts CI.
    """
    # Pour declarer un contrat CLI explicite et versionnable.
    parser = argparse.ArgumentParser(prog="krpsim_verif")
    # Pour figer l'interface publique attendue par les scripts externes.
    parser.add_argument("config", help="configuration file path")
    # Pour figer l'interface publique attendue par les scripts externes.
    parser.add_argument("trace", help="execution trace file path")
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
        "--analysis-log",
        action="store_true",
        help="print detailed analysis logs for CLI pipeline and verification",
    )
    # Pour figer l'interface publique attendue par les scripts externes.
    parser.add_argument("--log", help="file to write logs to")
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return parser


def _configure_logging(args: argparse.Namespace) -> None:
    """Configure verification CLI log sinks."""
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if args.log:
        handlers.append(logging.FileHandler(args.log))
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(message)s",
        handlers=handlers,
        force=True,
    )


def _verify_inputs(
    args: argparse.Namespace, logger: AnalysisLogger
) -> tuple[Simulator | None, int]:
    """Run verification and print its stable error messages."""
    try:
        sim = verify_files(Path(args.config), Path(args.trace))
    except ParseError as exc:
        logger.log_step("PARSE_ERROR", str(exc), scope="main")
        logging.error("invalid config: %s", exc)
        print(f"invalid config: {exc}")
        return None, 1
    except (OSError, TraceError) as exc:
        logger.log_step("TRACE_ERROR", str(exc), scope="main")
        logging.error("invalid trace: %s", exc)
        print(f"invalid trace: {exc}")
        return None, 1
    logger.log_step("TRACE_VALID", scope="main")
    logging.info("trace is valid")
    print("trace is valid")
    return sim, 0


def _print_final_stocks(sim: Simulator, logger: AnalysisLogger, scope: str) -> None:
    """Print the final stock snapshot for a successful verification."""
    stock_names = sorted(sim.config.all_stock_names())
    logger.log_key_value("FINAL_STOCK_NAMES", stock_names, scope=scope)
    max_len = max((len(name) for name in stock_names), default=0)
    logger.log_key_value(
        "FINAL_STOCKS",
        {name: sim.stocks.get(name, 0) for name in stock_names},
        scope=scope,
    )
    logger.log_key_value("LAST_CYCLE", sim.time, scope=scope)
    print("Final Stocks:")
    for name in stock_names:
        print(f"  {name:<{max_len}}  => {sim.stocks.get(name, 0)}")
    print(f"Last cycle: {sim.time}")


# Pour isoler main et faciliter son evolution sous tests.
def main(argv: list[str] | None = None) -> int:
    """Point d'entree principal du binaire ``krpsim_verif``.

    Parameters:
        argv: Liste d'arguments optionnelle pour tests et appels internes.

    Returns:
        ``0`` si la trace est valide, ``1`` sinon.

    Raises:
        Aucune exception n'est propagee volontairement a l'appelant.

    Contrat:
        Toute erreur fonctionnelle doit etre transformee en message lisible
        et en code retour non nul.
    """
    # Pour conserver un point unique de configuration des arguments.
    parser = build_parser()
    # Pour permettre l'injection d'arguments en test unitaire.
    args = parser.parse_args(argv)
    # Pour etiqueter clairement les logs emis par cette fonction.
    scope = "main"
    # Pour centraliser les traces d'analyse du comportement de la CLI.
    analysis_logger = AnalysisLogger(enabled=args.analysis_log)
    # Pour partager le logger d'analyse avec le module de verification.
    set_active_analysis_logger(analysis_logger)
    # Pour partager le meme logger avec la simulation de reference appelee ici.
    set_krpsim_analysis_logger(analysis_logger)
    # Pour exposer les arguments parsees dans un bloc d'entree unique.
    analysis_logger.log_header("CLI ENTRYPOINT", scope=scope)
    # Pour garder un format deterministe pour reproduire un run exact.
    analysis_logger.log_key_value("PARSED_ARGS", vars(args), scope=scope)

    _configure_logging(args)

    # Pour tracer les chemins qui seront transmis au coeur de verification.
    analysis_logger.log_header("VERIFICATION PIPELINE", scope=scope)
    # Pour exposer le fichier de configuration demande.
    analysis_logger.log_key_value("CONFIG_PATH", args.config, scope=scope)
    # Pour exposer le fichier de trace demande.
    analysis_logger.log_key_value("TRACE_PATH", args.trace, scope=scope)
    sim, exit_code = _verify_inputs(args, analysis_logger)

    # Pour traiter explicitement un cas d'entree invalide ou absent.
    if sim is not None:
        _print_final_stocks(sim, analysis_logger, scope)
    # Pour tracer la valeur de sortie renvoyee au shell.
    analysis_logger.log_key_value("EXIT_CODE", exit_code, scope=scope)
    # Pour fournir au shell un code retour exploitable en automatisation.
    return exit_code


# Pour proteger un invariant de comparaison critique ici.
if __name__ == "__main__":
    # Pour signaler sans delai une violation explicite du contrat.
    raise SystemExit(main())
