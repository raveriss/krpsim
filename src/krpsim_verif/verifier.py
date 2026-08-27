"""Utilitaires de verification de trace pour KRPSIM.

Ce module compare une trace textuelle a la trace attendue produite par le
simulateur et retourne l'etat final si la verification reussit.
"""

# Pour retarder l'evaluation des types et limiter les cycles.
from __future__ import annotations

# Pour rendre le diagnostic activable sans polluer la sortie.
import logging

# Pour formaliser des contrats de donnees clairs et compacts.
from dataclasses import dataclass

# Pour eviter les chemins fragiles relies aux separateurs OS.
from pathlib import Path

# Pour reutiliser la logique canonique du simulateur sans duplication.
from krpsim.parser import Config, parse_file

# Pour reutiliser la logique canonique du simulateur sans duplication.
from krpsim.simulator import Simulator

# Pour partager les logs d'analyse entre la CLI et le verificateur.
from logger.analysis_log_krpsim_verif import AnalysisLogger, get_active_analysis_logger


# Pour encapsuler TraceError autour d'un contrat clairement borne.
class TraceError(Exception):
    """Signale une incoherence de trace par rapport a la configuration."""


# Pour fiabiliser les objets metier via un schema declaratif.
@dataclass
# Pour encapsuler TraceEntry autour d'un contrat clairement borne.
class TraceEntry:
    """Represente un evenement elementaire d'une trace machine.

    Attributes:
        cycle: Cycle de demarrage du processus.
        process: Nom du processus demarre.

    Contrat:
        L'ordre des entrees dans la liste conserve l'ordre de la trace source.
    """

    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    cycle: int
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    process: str


def _serialize_config(config: Config) -> dict[str, object]:
    """Retourne une representation lisible de la configuration verifiee."""
    return {
        "stocks": config.stocks,
        "processes": {
            name: {
                "name": process.name,
                "needs": process.needs,
                "results": process.results,
                "delay": process.delay,
            }
            for name, process in config.processes.items()
        },
        "optimize": config.optimize,
    }


def _serialize_trace_entry(entry: TraceEntry) -> dict[str, object]:
    """Retourne une entree de trace dans un format stable pour les logs."""
    return {"cycle": entry.cycle, "process": entry.process}


def _serialize_simulator_state(sim: Simulator) -> dict[str, object]:
    """Retourne un snapshot complet et lisible de l'etat du simulateur."""
    return {
        "config": _serialize_config(sim.config),
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


# Pour isoler parse_trace et faciliter son evolution sous tests.
def parse_trace(path: Path) -> list[TraceEntry]:
    """Parse un fichier de trace au format ``cycle:process``.

    Parameters:
        path: Chemin du fichier de trace a verifier.

    Returns:
        Liste d'entrees de trace ordonnee.

    Raises:
        OSError:
            Si le fichier ne peut pas etre lu.
        TraceError:
            Si une ligne viole le format attendu.

    Contrat:
        La premiere erreur rencontree doit interrompre le parsing pour
        produire un diagnostic localise.
    """
    # Pour garder un canal de diagnostic coherent dans tout le module.
    logger = logging.getLogger(__name__)
    # Pour obtenir le logger d'analyse partage avec la couche CLI.
    analysis_logger = get_active_analysis_logger()
    # Pour etiqueter clairement les logs emis par cette fonction.
    scope = "parse_trace"
    # Pour exposer clairement la phase de lecture de trace.
    analysis_logger.log_header("TRACE PARSING", scope=scope)
    # Pour tracer la cible exacte lue par le parser.
    analysis_logger.log_key_value("TRACE_PATH", str(path), scope=scope)
    # Pour charger la trace complete avant validation ligne par ligne.
    lines = path.read_text().splitlines()
    # Pour exposer les lignes brutes avant filtrage et validation.
    analysis_logger.log_key_value("RAW_TRACE_LINES", lines, scope=scope)
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    entries: list[TraceEntry] = []
    # Pour appliquer uniformement la regle a chaque element concerne.
    for idx, line in enumerate(lines, start=1):
        # Pour tracer chaque ligne avant decision de parsing.
        analysis_logger.log_key_value(
            "TRACE_LINE_READ",
            {"line_number": idx, "content": line},
            scope=scope,
        )
        # Pour traiter explicitement un cas d'entree invalide ou absent.
        if not line:
            # Pour localiser l'erreur avant propagation au niveau CLI.
            analysis_logger.log_step(
                "TRACE_LINE_ERROR",
                {"line_number": idx, "reason": "empty"},
                scope=scope,
            )
            # Pour signaler sans delai une violation explicite du contrat.
            raise TraceError(f"empty trace line {idx}")
        # Pour expliciter une decision qui impacte le flux metier.
        if line.startswith("#"):
            # Pour rendre visible le filtrage des commentaires.
            analysis_logger.log_step(
                "TRACE_LINE_SKIPPED",
                {"line_number": idx, "reason": "comment"},
                scope=scope,
            )
            # Pour ignorer ce cas et laisser la boucle traiter les suivants.
            continue
        # Pour traiter explicitement un cas d'entree invalide ou absent.
        if ":" not in line:
            # Pour localiser l'erreur avant propagation au niveau CLI.
            analysis_logger.log_step(
                "TRACE_LINE_ERROR",
                {"line_number": idx, "reason": "missing_separator"},
                scope=scope,
            )
            # Pour signaler sans delai une violation explicite du contrat.
            raise TraceError(f"invalid trace line {idx}: '{line}'")
        # Pour eviter de casser un nom de process contenant des deux-points.
        cycle_str, name = line.split(":", 1)
        # Pour traiter explicitement un cas d'entree invalide ou absent.
        if not cycle_str.isdigit():
            # Pour localiser l'erreur avant propagation au niveau CLI.
            analysis_logger.log_step(
                "TRACE_LINE_ERROR",
                {
                    "line_number": idx,
                    "reason": "invalid_cycle",
                    "cycle": cycle_str,
                },
                scope=scope,
            )
            # Pour signaler sans delai une violation explicite du contrat.
            raise TraceError(f"invalid trace line {idx}: '{line}'")
        # Pour normaliser chaque evenement avant comparaison stricte.
        entry = TraceEntry(int(cycle_str), name)
        # Pour exposer la forme structuree issue de la ligne courante.
        analysis_logger.log_key_value(
            "TRACE_ENTRY_PARSED",
            _serialize_trace_entry(entry),
            scope=scope,
        )
        # Pour journaliser les entrees lues en mode diagnostic.
        logger.info("%d:%s", entry.cycle, entry.process)
        # Pour conserver l'ordre original de la trace verifiee.
        entries.append(entry)
    # Pour exposer le resultat complet de la phase de parsing.
    analysis_logger.log_key_value(
        "PARSED_TRACE_ENTRIES",
        [_serialize_trace_entry(entry) for entry in entries],
        scope=scope,
    )
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return entries


# Pour isoler _expected_trace et faciliter son evolution sous tests.
def _expected_trace(
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    config: Config,
    max_time: int,
    # Pour ouvrir un bloc qui porte une contrainte locale explicite.
) -> tuple[list[TraceEntry], Simulator]:
    """Produit la trace canonique attendue pour ``config``.

    Parameters:
        config: Configuration metier deja validee.
        max_time: Cycle limite a reproduire pour comparaison.

    Returns:
        Un tuple ``(trace_attendue, simulateur_final)``.

    Raises:
        Aucune exception n'est levee explicitement.

    Contrat:
        Le verificateur doit reexecuter la meme logique que le simulateur
        pour comparer sur une base strictement equivalente.
    """
    # Pour obtenir le logger d'analyse partage avec la couche CLI.
    analysis_logger = get_active_analysis_logger()
    # Pour etiqueter clairement les logs emis par cette fonction.
    scope = "_expected_trace"
    # Pour isoler la reconstruction de trace attendue dans les logs.
    analysis_logger.log_header("EXPECTED TRACE", scope=scope)
    # Pour exposer la borne temporelle utilisee pour rejouer la simulation.
    analysis_logger.log_key_value("MAX_TIME", max_time, scope=scope)
    # Pour exposer les donnees source de la simulation de reference.
    analysis_logger.log_key_value("CONFIG", _serialize_config(config), scope=scope)
    # Pour executer la logique metier via l'implementation de reference.
    sim = Simulator(config)
    # Pour exposer l'etat initial du moteur de reference.
    analysis_logger.log_key_value(
        "SIMULATOR_STATE_AFTER_INIT",
        _serialize_simulator_state(sim),
        scope=scope,
    )
    # Pour produire l'etat de reference a partir du moteur unique.
    raw = sim.run(max_time)
    # Pour exposer la trace brute produite par le moteur.
    analysis_logger.log_key_value("EXPECTED_TRACE_RAW", raw, scope=scope)
    # Pour separer explicitement les etats intermediaires du traitement.
    entries = [TraceEntry(cycle, name) for cycle, name in raw]
    # Pour exposer la trace attendue dans le meme schema que la trace lue.
    analysis_logger.log_key_value(
        "EXPECTED_TRACE_ENTRIES",
        [_serialize_trace_entry(entry) for entry in entries],
        scope=scope,
    )
    # Pour exposer l'etat final de reference associe a cette trace.
    analysis_logger.log_key_value(
        "SIMULATOR_STATE_AFTER_RUN",
        _serialize_simulator_state(sim),
        scope=scope,
    )
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return entries, sim


def _verify_empty_trace(
    config: Config, analysis_logger: AnalysisLogger, scope: str
) -> Simulator:
    """Validate and execute the special empty-trace case."""
    if not config.optimize:
        for proc in config.processes.values():
            can_start = all(config.stocks.get(n, 0) >= q for n, q in proc.needs.items())
            analysis_logger.log_key_value(
                "EMPTY_TRACE_PROCESS_CHECK",
                {
                    "process_name": proc.name,
                    "needs": proc.needs,
                    "initial_stocks": config.stocks,
                    "can_start": can_start,
                },
                scope=scope,
            )
            if can_start:
                analysis_logger.log_step(
                    "EMPTY_TRACE_ERROR", f"process '{proc.name}' can start", scope=scope
                )
                raise TraceError("empty trace")
    sim = Simulator(config)
    analysis_logger.log_step("EMPTY_TRACE_SIM_RUN_START", {"max_time": 0}, scope)
    sim.run(0)
    analysis_logger.log_key_value(
        "SIMULATOR_STATE_AFTER_EMPTY_TRACE_RUN",
        _serialize_simulator_state(sim),
        scope=scope,
    )
    return sim


def _trace_run_until(
    config: Config, trace: list[TraceEntry], analysis_logger: AnalysisLogger, scope: str
) -> int:
    """Resolve the simulation horizon required to reproduce a trace."""
    run_until = 0
    for entry in trace:
        process = config.processes.get(entry.process)
        analysis_logger.log_key_value(
            "TRACE_ENTRY_PROCESS_LOOKUP",
            {
                "entry": _serialize_trace_entry(entry),
                "process_found": process is not None,
                "process_delay": process.delay if process else None,
            },
            scope=scope,
        )
        if process is None:
            analysis_logger.log_step(
                "UNKNOWN_PROCESS_ERROR", entry.process, scope=scope
            )
            raise TraceError(f"unknown process '{entry.process}' in trace")
        candidate = entry.cycle + process.delay
        run_until = max(run_until, candidate)
    return run_until


def _compare_traces(
    expected: list[TraceEntry],
    trace: list[TraceEntry],
    analysis_logger: AnalysisLogger,
    scope: str,
) -> None:
    """Raise a precise error when input and expected traces diverge."""
    for idx, (got, exp) in enumerate(zip(trace, expected), start=1):
        analysis_logger.log_key_value(
            "TRACE_COMPARE",
            {
                "line": idx,
                "got": _serialize_trace_entry(got),
                "expected": _serialize_trace_entry(exp),
            },
            scope=scope,
        )
        if got != exp:
            analysis_logger.log_step("TRACE_MISMATCH_ERROR", {"line": idx}, scope=scope)
            raise TraceError(
                f"line {idx}: expected {exp.cycle}:{exp.process} "
                f"but got {got.cycle}:{got.process}"
            )
    if len(trace) > len(expected):
        analysis_logger.log_step(
            "TRACE_EXTRA_EVENTS_ERROR",
            {"first_extra_line": len(expected) + 1},
            scope=scope,
        )
        raise TraceError(f"trace has extra events starting at line {len(expected)+1}")


# Pour isoler verify_trace et faciliter son evolution sous tests.
def verify_trace(config: Config, trace: list[TraceEntry]) -> Simulator:
    """Valide une trace par rapport a une configuration donnee.

    Parameters:
        config: Configuration de reference.
        trace: Entrees de trace deja parsees.

    Returns:
        L'etat final du simulateur correspondant a la trace validee.

    Raises:
        TraceError:
            Si un ecart est detecte entre trace fournie et trace attendue.

    Contrat:
        La verification s'arrete sur le premier ecart pour garder un message
        de diagnostic directement exploitable.
    """
    # Pour garder un canal de diagnostic coherent dans tout le module.
    logger = logging.getLogger(__name__)
    # Pour obtenir le logger d'analyse partage avec la couche CLI.
    analysis_logger = get_active_analysis_logger()
    # Pour etiqueter clairement les logs emis par cette fonction.
    scope = "verify_trace"
    # Pour exposer clairement la phase de comparaison metier.
    analysis_logger.log_header("TRACE VERIFICATION", scope=scope)
    # Pour tracer la configuration qui sert de reference.
    analysis_logger.log_key_value("CONFIG", _serialize_config(config), scope=scope)
    # Pour tracer la trace fournie apres parsing.
    analysis_logger.log_key_value(
        "INPUT_TRACE",
        [_serialize_trace_entry(entry) for entry in trace],
        scope=scope,
    )

    if not trace:
        analysis_logger.log_step("EMPTY_TRACE_BRANCH", scope=scope)
        sim = _verify_empty_trace(config, analysis_logger, scope)
        # Pour laisser une preuve exploitable du succes de verification.
        logger.info("trace validated successfully")
        # Pour marquer la fin positive de cette branche.
        analysis_logger.log_step("VERIFICATION_SUCCESS", "empty trace", scope=scope)
        # Pour rendre a l'appelant le resultat promis par le contrat.
        return sim

    run_until = _trace_run_until(config, trace, analysis_logger, scope)
    # Pour comparer la trace utilisateur a une reference reproduite.
    expected, sim = _expected_trace(config, run_until)
    # Pour exposer les deux tailles avant comparaison element par element.
    analysis_logger.log_key_value(
        "TRACE_LENGTHS",
        {"input": len(trace), "expected": len(expected), "run_until": run_until},
        scope=scope,
    )
    _compare_traces(expected, trace, analysis_logger, scope)

    # Pour laisser une preuve exploitable du succes de verification.
    logger.info("trace validated successfully")
    # Pour exposer l'etat final valide apres comparaison.
    analysis_logger.log_key_value(
        "FINAL_SIMULATOR_STATE",
        _serialize_simulator_state(sim),
        scope=scope,
    )
    # Pour marquer la fin positive du controle.
    analysis_logger.log_step("VERIFICATION_SUCCESS", scope=scope)
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return sim


# Pour isoler verify_files et faciliter son evolution sous tests.
def verify_files(config_path: Path, trace_path: Path) -> Simulator:
    """Verifie directement deux fichiers de configuration et de trace.

    Parameters:
        config_path: Chemin vers le fichier de configuration.
        trace_path: Chemin vers le fichier de trace.

    Returns:
        Etat final du simulateur apres verification complete.

    Raises:
        ParseError:
            Propagee depuis ``parse_file`` si la configuration est invalide.
        OSError:
            Si le fichier de trace est inaccessible.
        TraceError:
            Si la trace ne correspond pas a la simulation attendue.

    Contrat:
        Cette fonction sert de point d'entree unique pour la CLI afin de
        conserver un flux de verification coherent.
    """
    # Pour garder un canal de diagnostic coherent dans tout le module.
    logger = logging.getLogger(__name__)
    # Pour obtenir le logger d'analyse partage avec la couche CLI.
    analysis_logger = get_active_analysis_logger()
    # Pour etiqueter clairement les logs emis par cette fonction.
    scope = "verify_files"
    # Pour exposer clairement la phase fichier du verificateur.
    analysis_logger.log_header("FILE VERIFICATION", scope=scope)
    # Pour tracer les chemins exacts recus par l'appelant.
    analysis_logger.log_key_value("CONFIG_PATH", str(config_path), scope=scope)
    # Pour tracer les chemins exacts recus par l'appelant.
    analysis_logger.log_key_value("TRACE_PATH", str(trace_path), scope=scope)
    # Pour reutiliser la validation canonique plutot qu'un parsing local.
    config = parse_file(config_path)
    # Pour exposer la configuration validee avant comparaison.
    analysis_logger.log_key_value(
        "PARSED_CONFIG",
        _serialize_config(config),
        scope=scope,
    )
    # Pour verifier la syntaxe de trace avant toute comparaison metier.
    trace = parse_trace(trace_path)
    # Pour exposer le resultat de parsing transmis a la verification.
    analysis_logger.log_key_value(
        "PARSED_TRACE",
        [_serialize_trace_entry(entry) for entry in trace],
        scope=scope,
    )
    # Pour tracer clairement la paire de fichiers en cours de controle.
    logger.info("verifying trace against %s", config_path)
    # Pour indiquer le passage a la verification metier.
    analysis_logger.log_step("VERIFY_TRACE_START", scope=scope)
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return verify_trace(config, trace)
