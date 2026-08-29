"""Utilitaires de verification de trace pour KRPSIM.

Ce module compare une trace textuelle a la trace attendue produite par le
simulateur et retourne l'etat final si la verification reussit.
"""

# Pour retarder l'evaluation des types et limiter les cycles.
from __future__ import annotations

# Pour rendre le diagnostic activable sans polluer la sortie.
import heapq
import logging
import sys

# Pour formaliser des contrats de donnees clairs et compacts.
from dataclasses import dataclass

# Pour eviter les chemins fragiles relies aux separateurs OS.
from pathlib import Path

# Pour reutiliser la logique canonique du simulateur sans duplication.
from krpsim.parser import Config, Process, parse_file

# Pour reutiliser la logique canonique du simulateur sans duplication.
from krpsim.simulator import Simulator

# Pour partager les logs d'analyse entre la CLI et le verificateur.
from logger.analysis_log_krpsim_verif import AnalysisLogger, get_active_analysis_logger


# Pour encapsuler TraceError autour d'un contrat clairement borne.
class TraceError(Exception):
    """Signale une incoherence de trace par rapport a la configuration."""


# Pour fiabiliser les objets metier via un schema declaratif.
@dataclass(slots=True)
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


@dataclass
class _VerificationState:
    """État mutable minimal nécessaire au rejeu d'une trace."""

    stocks: dict[str, int]
    running: list[tuple[int, int, Process]]
    previous_cycle: int = 0
    last_cycle: int = 0
    sequence: int = 0


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
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    entries: list[TraceEntry] = []
    # Pour appliquer uniformement la regle a chaque element concerne.
    with path.open(encoding="utf-8") as stream:
        lines = enumerate(stream, start=1)
        for idx, raw_line in lines:
            line = raw_line.rstrip("\n")
            _parse_trace_line(line, idx, entries, logger, analysis_logger, scope)
    analysis_logger.log_key_value("PARSED_TRACE_COUNT", len(entries), scope=scope)
    return entries


def _parse_trace_line(
    line: str,
    idx: int,
    entries: list[TraceEntry],
    logger: logging.Logger,
    analysis_logger: AnalysisLogger,
    scope: str,
) -> None:
    """Valide une ligne et l'ajoute a la trace structuree."""

    analysis_logger.log_key_value(
        "TRACE_LINE_READ", {"line_number": idx, "content": line}, scope=scope
    )
    if not line:
        analysis_logger.log_step(
            "TRACE_LINE_ERROR",
            {"line_number": idx, "reason": "empty"},
            scope=scope,
        )
        raise TraceError(f"empty trace line {idx}")
    if line.startswith("#"):
        analysis_logger.log_step(
            "TRACE_LINE_SKIPPED",
            {"line_number": idx, "reason": "comment"},
            scope=scope,
        )
        return
    if ":" not in line:
        analysis_logger.log_step(
            "TRACE_LINE_ERROR",
            {"line_number": idx, "reason": "missing_separator"},
            scope=scope,
        )
        raise TraceError(f"invalid trace line {idx}: '{line}'")
    cycle_str, name = line.split(":", 1)
    if not cycle_str.isdigit() or not name:
        analysis_logger.log_step(
            "TRACE_LINE_ERROR",
            {
                "line_number": idx,
                "reason": "invalid_cycle",
                "cycle": cycle_str,
            },
            scope=scope,
        )
        raise TraceError(f"invalid trace line {idx}: '{line}'")
    entry = TraceEntry(int(cycle_str), sys.intern(name))
    analysis_logger.log_key_value(
        "TRACE_ENTRY_PARSED", _serialize_trace_entry(entry), scope=scope
    )
    logger.info("%d:%s", entry.cycle, entry.process)
    entries.append(entry)


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
    return Simulator(config)


def _complete_until(
    cycle: int,
    running: list[tuple[int, int, Process]],
    stocks: dict[str, int],
) -> int:
    """Credite toutes les productions terminees avant un cycle donne."""

    last_completion = 0
    while running and running[0][0] <= cycle:
        completion, _, process = heapq.heappop(running)
        last_completion = max(last_completion, completion)
        for resource, quantity in process.results.items():
            stocks[resource] = stocks.get(resource, 0) + quantity
    return last_completion


def _resolve_process(config: Config, process_name: str) -> Process:
    """Retourne le processus demandé ou signale une entrée inconnue."""

    process = config.processes.get(process_name)
    if process is None:
        raise TraceError(f"unknown process '{process_name}' in trace")
    return process


def _missing_resources(process: Process, stocks: dict[str, int]) -> dict[str, int]:
    """Calcule les quantités absentes pour une exécution."""

    return {
        resource: quantity - stocks.get(resource, 0)
        for resource, quantity in process.needs.items()
        if stocks.get(resource, 0) < quantity
    }


def _consume_and_schedule(
    entry: TraceEntry,
    process: Process,
    state: _VerificationState,
) -> None:
    """Consomme les entrées et crédite ou programme les résultats."""

    for resource, quantity in process.needs.items():
        state.stocks[resource] -= quantity
    if process.delay == 0:
        for resource, quantity in process.results.items():
            state.stocks[resource] = state.stocks.get(resource, 0) + quantity
        return
    state.sequence += 1
    heapq.heappush(
        state.running,
        (entry.cycle + process.delay, state.sequence, process),
    )


def _verify_entry(
    config: Config,
    entry: TraceEntry,
    line_number: int,
    state: _VerificationState,
) -> None:
    """Valide puis applique une entrée individuelle de trace."""

    if entry.cycle < state.previous_cycle:
        raise TraceError(
            f"line {line_number}: cycle {entry.cycle} is before "
            f"cycle {state.previous_cycle}"
        )
    completion = _complete_until(entry.cycle, state.running, state.stocks)
    state.last_cycle = max(state.last_cycle, completion)
    process = _resolve_process(config, entry.process)
    missing = _missing_resources(process, state.stocks)
    if missing:
        raise TraceError(
            f"line {line_number} at cycle {entry.cycle}: process "
            f"'{process.name}' lacks resources {missing}"
        )
    _consume_and_schedule(entry, process, state)
    state.previous_cycle = entry.cycle
    state.last_cycle = max(state.last_cycle, entry.cycle)


def _build_verified_simulator(config: Config, state: _VerificationState) -> Simulator:
    """Finalise les productions et matérialise l'état validé."""

    completion = _complete_until(2**63 - 1, state.running, state.stocks)
    state.last_cycle = max(state.last_cycle, completion)
    sim = Simulator(config)
    sim.stocks = state.stocks
    sim.time = state.last_cycle
    sim._max_time = state.last_cycle
    return sim


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
    analysis_logger.log_key_value("INPUT_TRACE_COUNT", len(trace), scope=scope)

    if not trace:
        analysis_logger.log_step("EMPTY_TRACE_BRANCH", scope=scope)
        sim = _verify_empty_trace(config, analysis_logger, scope)
        # Pour laisser une preuve exploitable du succes de verification.
        logger.info("trace validated successfully")
        # Pour marquer la fin positive de cette branche.
        analysis_logger.log_step("VERIFICATION_SUCCESS", "empty trace", scope=scope)
        # Pour rendre a l'appelant le resultat promis par le contrat.
        return sim

    state = _VerificationState(config.stocks.copy(), [])
    for line_number, entry in enumerate(trace, start=1):
        _verify_entry(config, entry, line_number, state)

    sim = _build_verified_simulator(config, state)

    # Pour laisser une preuve exploitable du succes de verification.
    logger.info("trace validated successfully")
    # Pour exposer l'etat final valide apres comparaison.
    analysis_logger.log_key_value("FINAL_STOCKS", sim.stocks, scope=scope)
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
    analysis_logger.log_key_value("PARSED_TRACE_COUNT", len(trace), scope=scope)
    # Pour tracer clairement la paire de fichiers en cours de controle.
    logger.info("verifying trace against %s", config_path)
    # Pour indiquer le passage a la verification metier.
    analysis_logger.log_step("VERIFY_TRACE_START", scope=scope)
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return verify_trace(config, trace)
