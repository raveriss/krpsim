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
    # Pour charger la trace complete avant validation ligne par ligne.
    lines = path.read_text().splitlines()
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    entries: list[TraceEntry] = []
    # Pour appliquer uniformement la regle a chaque element concerne.
    for idx, line in enumerate(lines, start=1):
        # Pour traiter explicitement un cas d'entree invalide ou absent.
        if not line:
            # Pour signaler sans delai une violation explicite du contrat.
            raise TraceError(f"empty trace line {idx}")
        # Pour expliciter une decision qui impacte le flux metier.
        if line.startswith("#"):
            # Pour ignorer ce cas et laisser la boucle traiter les suivants.
            continue
        # Pour traiter explicitement un cas d'entree invalide ou absent.
        if ":" not in line:
            # Pour signaler sans delai une violation explicite du contrat.
            raise TraceError(f"invalid trace line {idx}: '{line}'")
        # Pour eviter de casser un nom de process contenant des deux-points.
        cycle_str, name = line.split(":", 1)
        # Pour traiter explicitement un cas d'entree invalide ou absent.
        if not cycle_str.isdigit():
            # Pour signaler sans delai une violation explicite du contrat.
            raise TraceError(f"invalid trace line {idx}: '{line}'")
        # Pour normaliser chaque evenement avant comparaison stricte.
        entry = TraceEntry(int(cycle_str), name)
        # Pour journaliser les entrees lues en mode diagnostic.
        logger.info("%d:%s", entry.cycle, entry.process)
        # Pour conserver l'ordre original de la trace verifiee.
        entries.append(entry)
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return entries


# Pour isoler _expected_trace et faciliter son evolution sous tests.
def _expected_trace(
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    config: Config, max_time: int
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
    # Pour executer la logique metier via l'implementation de reference.
    sim = Simulator(config)
    # Pour produire l'etat de reference a partir du moteur unique.
    raw = sim.run(max_time)
    # Pour separer explicitement les etats intermediaires du traitement.
    entries = [TraceEntry(cycle, name) for cycle, name in raw]
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return entries, sim


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

    # Pour traiter explicitement le cas de trace vide a verifier.
    if not trace:
        # Pour appliquer la logique specifique au mode optimisation.
        if not config.optimize:
            # Pour appliquer uniformement la regle a chaque element concerne.
            for proc in config.processes.values():
                # Pour proteger un invariant de comparaison critique ici.
                if all(config.stocks.get(n, 0) >= q for n, q in proc.needs.items()):
                    # Pour signaler sans delai une violation explicite du
                    # contrat.
                    raise TraceError("empty trace")
        # Pour executer la logique metier via l'implementation de reference.
        sim = Simulator(config)
        # Pour valider un etat final minimal quand la trace est vide.
        sim.run(0)
        # Pour laisser une preuve exploitable du succes de verification.
        logger.info("trace validated successfully")
        # Pour rendre a l'appelant le resultat promis par le contrat.
        return sim

    # Pour borner la simulation en tenant compte de tous les evenements.
    run_until = 0
    # Pour appliquer uniformement la regle a chaque element concerne.
    for entry in trace:
        # Pour isoler une etape de validation et garder un diagnostic clair.
        process = config.processes.get(entry.process)
        # Pour arreter la verification sur une reference de processus inconnue.
        if process is None:
            # Pour signaler sans delai une violation explicite du contrat.
            raise TraceError(f"unknown process '{entry.process}' in trace")
        # Pour inclure les processus lents demarres au meme cycle que le dernier.
        run_until = max(run_until, entry.cycle + process.delay)
    # Pour comparer la trace utilisateur a une reference reproduite.
    expected, sim = _expected_trace(config, run_until)
    # Pour appliquer uniformement la regle a chaque element concerne.
    for idx, (got, exp) in enumerate(zip(trace, expected), start=1):
        # Pour expliciter une decision qui impacte le flux metier.
        if got != exp:
            # Pour signaler sans delai une violation explicite du contrat.
            raise TraceError(
                # Pour localiser precisement la divergence dans la trace.
                f"line {idx}: expected {exp.cycle}:{exp.process} "
                # Pour fournir un ecart exact et directement actionnable.
                f"but got {got.cycle}:{got.process}"
            # Pour clore le bloc sans ambiguite de structure.
            )

    # Pour rejeter une trace qui declare des evenements non reproductibles.
    if len(trace) > len(expected):
        # Pour signaler sans delai une violation explicite du contrat.
        raise TraceError(f"trace has extra events starting at line {len(expected)+1}")

    # Pour laisser une preuve exploitable du succes de verification.
    logger.info("trace validated successfully")
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
    # Pour reutiliser la validation canonique plutot qu'un parsing local.
    config = parse_file(config_path)
    # Pour verifier la syntaxe de trace avant toute comparaison metier.
    trace = parse_trace(trace_path)
    # Pour tracer clairement la paire de fichiers en cours de controle.
    logger.info("verifying trace against %s", config_path)
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return verify_trace(config, trace)
