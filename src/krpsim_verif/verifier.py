"""Utilitaires de verification de trace pour KRPSIM.

Ce module compare une trace textuelle a la trace attendue produite par le
simulateur et retourne l'etat final si la verification reussit.
"""

# Pour retarder l'evaluation des types et limiter les cycles.
from __future__ import annotations

import heapq
import sys

# Pour formaliser des contrats de donnees clairs et compacts.
from dataclasses import dataclass

# Pour eviter les chemins fragiles relies aux separateurs OS.
from pathlib import Path

# Pour reutiliser la logique canonique du simulateur sans duplication.
from krpsim.parser import Config, Process, parse_file

# Pour reutiliser la logique canonique du simulateur sans duplication.
from krpsim.simulator import Simulator


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
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    entries: list[TraceEntry] = []
    # Pour appliquer uniformement la regle a chaque element concerne.
    with path.open(encoding="utf-8") as stream:
        lines = enumerate(stream, start=1)
        for idx, raw_line in lines:
            line = raw_line.rstrip("\n")
            _parse_trace_line(line, idx, entries)
    return entries


def _parse_trace_line(
    line: str,
    idx: int,
    entries: list[TraceEntry],
) -> None:
    """Valide une ligne et l'ajoute a la trace structuree."""

    if not line:
        raise TraceError(f"empty trace line {idx}")
    if line.startswith("#"):
        return
    if ":" not in line:
        raise TraceError(f"invalid trace line {idx}: '{line}'")
    cycle_str, name = line.split(":", 1)
    if not cycle_str.isdigit() or not name:
        raise TraceError(f"invalid trace line {idx}: '{line}'")
    entry = TraceEntry(int(cycle_str), sys.intern(name))
    entries.append(entry)


def _verify_empty_trace(config: Config) -> Simulator:
    """Validate and execute the special empty-trace case."""
    if not config.optimize:
        for proc in config.processes.values():
            can_start = all(config.stocks.get(n, 0) >= q for n, q in proc.needs.items())
            if can_start:
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

    if not trace:
        sim = _verify_empty_trace(config)
        # Pour rendre a l'appelant le resultat promis par le contrat.
        return sim

    state = _VerificationState(config.stocks.copy(), [])
    for line_number, entry in enumerate(trace, start=1):
        _verify_entry(config, entry, line_number, state)

    sim = _build_verified_simulator(config, state)

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
    # Pour reutiliser la validation canonique plutot qu'un parsing local.
    config = parse_file(config_path)
    # Pour verifier la syntaxe de trace avant toute comparaison metier.
    trace = parse_trace(trace_path)
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return verify_trace(config, trace)
