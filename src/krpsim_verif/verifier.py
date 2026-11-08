# Le module rejoue les démarrages pour contrôler leur faisabilité.
"""Vérifie une trace KRPSIM et restitue son état final.

Chaque entrée décrit un démarrage au format ``cycle:process``. Le rejeu
consomme les besoins au démarrage et crédite les résultats à l'achèvement.
Une trace réalisable est acceptée sans exiger une solution optimale.
"""

# Les annotations différées évitent d'évaluer les types à la définition.
from __future__ import annotations

# La file de priorité permet de traiter les achèvements par date croissante.
import heapq

# sys.intern partage les noms répétés afin de limiter leur coût mémoire.
import sys

# Les classes de données définissent les champs nécessaires au rejeu.
from dataclasses import dataclass

# Path centralise l'accès aux fichiers de configuration et de trace.
from pathlib import Path

# Les règles et types du parseur constituent la référence de validation.
from krpsim.parser import Config, Process, parse_file

# Le résultat utilise le même objet d'état que le moteur de simulation.
from krpsim.simulator import Simulator


# Ce type distingue les incohérences de trace des erreurs d'accès aux fichiers.
class TraceError(Exception):
    # Le contrat permet aux appelants d'intercepter les rejets de validation.
    """Signale une syntaxe de trace invalide ou un démarrage irréalisable."""


# Les emplacements fixes réduisent la mémoire des nombreuses entrées de trace.
@dataclass(slots=True)
# Chaque entrée représente un démarrage, et non un achèvement.
class TraceEntry:
    # Les champs publics conservent le vocabulaire du format de trace.
    """Associe le cycle de démarrage au nom du processus demandé.

    ``cycle`` est un entier ; ``process`` contient un nom, pas un Process.
    La validation de l'ordre et des ressources intervient lors du rejeu.
    """

    # Le cycle détermine quelles productions sont disponibles au démarrage.
    cycle: int
    # Ce nom sert à retrouver la définition dans la configuration de référence.
    process: str


# Le constructeur rassemble les données mutables d'un seul rejeu.
@dataclass
# Cet état privé évite de modifier la configuration fournie par l'appelant.
class _VerificationState:
    # Le contrat précise notamment l'ordre des éléments de la file de priorité.
    """Suit les stocks, les opérations en cours et les cycles du rejeu.

    Chaque opération programmée contient son cycle de fin, un numéro unique
    de départage et sa définition Process. Les stocks sont modifiés sur place.
    """

    # Les quantités disponibles évoluent à chaque démarrage et achèvement.
    resource_stocks: dict[str, int]
    # La première opération est toujours celle dont l'achèvement est le plus
    # tôt.
    scheduled_processes: list[tuple[int, int, Process]]
    # Cette borne interdit de revenir avant le dernier démarrage accepté.
    previous_start_cycle: int = 0
    # Le temps final tient compte des démarrages comme des achèvements.
    last_event_cycle: int = 0
    # Le départage évite de comparer des objets Process à dates égales.
    scheduled_process_count: int = 0


# Cette entrée transforme le fichier en démarrages dans leur ordre d'origine.
def parse_trace(trace_file_path: Path) -> list[TraceEntry]:
    # La lecture valide la syntaxe ; la faisabilité relève de verify_trace.
    """Lit trace_file_path en UTF-8 et renvoie ses entrées ordonnées.

    Les commentaires commençant par '#' sont ignorés. Les lignes vides ou
    mal formées lèvent TraceError ; les erreurs de lecture sont propagées.
    Les diagnostics utilisent les numéros physiques de ligne du fichier.
    """
    # Cette collection ne reçoit que les démarrages syntaxiquement acceptés.
    trace_entries: list[TraceEntry] = []
    # Le contexte ferme le fichier même lorsqu'une ligne provoque une erreur.
    with trace_file_path.open(encoding="utf-8") as trace_stream:
        # Les numéros commencent à un pour correspondre aux éditeurs de texte.
        for line_number, raw_trace_line in enumerate(trace_stream, start=1):
            # Les espaces sont conservés car ils peuvent appartenir au nom.
            trace_line = raw_trace_line.rstrip("\n")
            # La même règle syntaxique s'applique à toutes les lignes physiques.
            _parse_trace_line(trace_line, line_number, trace_entries)
    # L'ordre source est nécessaire au contrôle chronologique ultérieur.
    return trace_entries


# Cette fonction localise les erreurs de syntaxe avant le rejeu des ressources.
def _parse_trace_line(
    # Le texte conserve les espaces du fichier, mais pas son saut de ligne.
    trace_line: str,
    # Le numéro source est utilisé uniquement dans les diagnostics.
    line_number: int,
    # La collection fournie reçoit l'entrée acceptée à sa fin.
    trace_entries: list[TraceEntry],
    # L'effet utile est l'ajout sur place, sans valeur de retour.
) -> None:
    # Le contrat distingue les lignes ignorées des lignes rejetées.
    """Ajoute un démarrage à trace_entries ou ignore un commentaire.

    Lève TraceError avec line_number si le format est invalide. La conversion
    du cycle en entier peut aussi propager ValueError pour certains caractères
    Unicode reconnus par isdigit mais non acceptés par int.
    """
    # Une ligne vide n'est pas un démarrage et constitue une erreur de format.
    if not trace_line:
        # Le numéro permet de corriger directement la ligne fautive.
        raise TraceError(f"empty trace line {line_number}")
    # Seul un '#' en première position marque un commentaire de trace.
    if trace_line.startswith("#"):
        # Aucun démarrage ne doit être créé pour cette ligne documentaire.
        return
    # Sans séparateur, le cycle et le nom ne peuvent pas être distingués.
    if ":" not in trace_line:
        # Le texte source aide à identifier le séparateur manquant.
        raise TraceError(f"invalid trace line {line_number}: '{trace_line}'")
    # Une seule séparation conserve les éventuels ':' du nom de processus.
    cycle_text, process_name = trace_line.split(":", 1)
    # Le format impose un cycle numérique et un nom non vide.
    if not cycle_text.isdigit() or not process_name:
        # Le diagnostic conserve le format commun aux erreurs de syntaxe.
        raise TraceError(f"invalid trace line {line_number}: '{trace_line}'")
    # sys.intern partage la chaîne entre les démarrages d'un même processus.
    trace_entry = TraceEntry(int(cycle_text), sys.intern(process_name))
    # L'ajout en fin préserve l'ordre des démarrages simultanés.
    trace_entries.append(trace_entry)


# La trace vide suit une règle distincte de celle des démarrages individuels.
def _verify_empty_trace(simulation_config: Config) -> Simulator:
    # Le contrat décrit la condition exacte de rejet de ce cas particulier.
    """Renvoie l'état initial si la trace vide est admissible.

    Sans objectif d'optimisation, lève TraceError si un processus peut démarrer
    avec les stocks initiaux. Avec un objectif, accepte la trace vide.
    """
    # La règle de rejet ne s'applique qu'en l'absence d'objectif configuré.
    if not simulation_config.optimize:
        # Un seul processus réalisable suffit à rendre la trace vide invalide.
        for process in simulation_config.processes.values():
            # Tous les besoins doivent être satisfaits pour autoriser un départ.
            can_start_process = all(
                # Une ressource absente est considérée comme un stock nul.
                simulation_config.stocks.get(resource_name, 0) >= required_quantity
                # Les besoins de cette opération constituent le seuil à
                # comparer.
                for resource_name, required_quantity in process.needs.items()
                # Le booléen résume la disponibilité de tous les besoins.
            )
            # Ce cas prouve qu'une opération était possible malgré la trace
            # vide.
            if can_start_process:
                # L'erreur conserve le diagnostic attendu par les appelants.
                raise TraceError("empty trace")
    # Sans démarrage, le résultat correspond aux stocks initiaux.
    return Simulator(simulation_config)


# Ce point central définit quand les productions deviennent disponibles.
def _complete_until(
    # La borne est inclusive pour autoriser un départ au cycle d'achèvement.
    target_cycle: int,
    # Cette file est ordonnée par cycle de fin puis numéro de départage.
    scheduled_processes: list[tuple[int, int, Process]],
    # Les productions terminées sont créditées directement dans ces stocks.
    resource_stocks: dict[str, int],
    # Le cycle renvoyé permet de mettre à jour le temps du rejeu.
) -> int:
    # Les effets sur les collections fournies font partie du contrat.
    """Crédite les achèvements jusqu'à target_cycle inclus, sur place.

    Retire ces opérations de scheduled_processes et augmente resource_stocks.
    Renvoie le dernier cycle achevé, ou zéro si aucune opération ne termine.
    """
    # Zéro représente l'absence d'achèvement durant cet appel.
    last_completion_cycle = 0
    # Seules les opérations déjà terminées peuvent alimenter les stocks.
    while scheduled_processes and scheduled_processes[0][0] <= target_cycle:
        # Le numéro de départage n'a plus d'utilité après extraction de la file.
        completion_cycle, _, completed_process = heapq.heappop(scheduled_processes)
        # Cette date contribue au temps final même sans nouveau démarrage.
        last_completion_cycle = max(last_completion_cycle, completion_cycle)
        # Un processus peut produire plusieurs ressources à son achèvement.
        for resource_name, produced_quantity in completed_process.results.items():
            # Une ressource produite pour la première fois part d'un stock nul.
            resource_stocks[resource_name] = (
                # La quantité produite s'ajoute au reliquat des opérations
                # passées.
                resource_stocks.get(resource_name, 0)
                # La production terminée augmente la quantité disponible.
                + produced_quantity
                # Le stock est disponible pour les démarrages suivants.
            )
    # L'appelant conserve la date maximale entre démarrages et achèvements.
    return last_completion_cycle


# La résolution des noms évite de rejouer une opération non configurée.
def _resolve_process(simulation_config: Config, process_name: str) -> Process:
    # Le contrat borne la recherche à la configuration de référence.
    """Renvoie le Process nommé ou lève TraceError s'il est inconnu."""
    # Le dictionnaire fournit la définition correspondant au nom de la trace.
    process = simulation_config.processes.get(process_name)
    # Une absence indique une incompatibilité entre la trace et la
    # configuration.
    if process is None:
        # Le nom incriminé permet de corriger la trace ou sa configuration.
        raise TraceError(f"unknown process '{process_name}' in trace")
    # La définition existante fournit les besoins, les résultats et le délai.
    return process


# Les déficits servent à la fois au refus de démarrage et à son explication.
def _compute_missing_resources(
    # Les besoins du processus fixent les quantités requises pour un démarrage.
    process: Process,
    # Les stocks incluent les productions achevées au cycle demandé.
    resource_stocks: dict[str, int],
    # Chaque nom renvoyé est associé à sa quantité manquante strictement
    # positive.
) -> dict[str, int]:
    # Ce calcul consulte les stocks sans les modifier.
    """Renvoie les déficits par ressource ; un dictionnaire vide autorise le départ."""
    # Seules les ressources bloquantes doivent figurer dans le diagnostic.
    return {
        # La différence exprime le complément nécessaire, pas le besoin total.
        resource_name: required_quantity - resource_stocks.get(resource_name, 0)
        # Chaque besoin est comparé au stock de la même ressource.
        for resource_name, required_quantity in process.needs.items()
        # Les ressources déjà suffisantes ne sont pas des causes de rejet.
        if resource_stocks.get(resource_name, 0) < required_quantity
        # Le dictionnaire obtenu permet également de décider si le départ est
        # valide.
    }


# Cette étape applique un démarrage dont les besoins ont déjà été contrôlés.
def _consume_and_schedule(
    # Le cycle de l'entrée sert d'origine au calcul de l'achèvement.
    trace_entry: TraceEntry,
    # La définition résolue fournit les consommations et productions.
    process: Process,
    # L'état du rejeu reçoit les débits et les opérations programmées.
    verification_state: _VerificationState,
    # Le rejeu se poursuit avec l'état modifié, sans résultat indépendant.
) -> None:
    # La précondition évite qu'un appel direct crée des stocks négatifs.
    """Débite les besoins et programme les résultats dans verification_state.

    Précondition : les besoins du processus sont disponibles. Un délai nul
    crédite les résultats immédiatement ; sinon, une opération est programmée.
    """
    # Les ressources sont réservées dès le départ, avant toute production.
    for resource_name, required_quantity in process.needs.items():
        # Le débit empêche un démarrage suivant de réutiliser les mêmes
        # ressources.
        verification_state.resource_stocks[resource_name] -= required_quantity
    # Une production immédiate doit être utilisable par l'entrée suivante.
    if process.delay == 0:
        # Tous les résultats de ce processus deviennent disponibles ensemble.
        for resource_name, produced_quantity in process.results.items():
            # Le stock précédent est nul si cette ressource n'existait pas
            # encore.
            available_quantity = verification_state.resource_stocks.get(
                # Le nom cible la ressource ; zéro couvre son absence initiale.
                resource_name,
                # Une ressource absente ne possède aucune unité disponible.
                0,
                # Cette quantité sert de base au crédit immédiat.
            )
            # Le stock inclut désormais cette production sans délai.
            verification_state.resource_stocks[resource_name] = (
                # Le reliquat disponible est conservé lors du crédit.
                available_quantity
                # La production terminée augmente la quantité disponible.
                + produced_quantity
                # La quantité sera visible par le prochain démarrage de la
                # trace.
            )
        # Cette sortie évite de programmer une seconde fois la production.
        return
    # Un numéro unique départage les fins simultanées sans comparer des Process.
    verification_state.scheduled_process_count += 1
    # L'achèvement est relatif au cycle demandé dans la trace.
    completion_cycle = trace_entry.cycle + process.delay
    # La file maintient les opérations en ordre de fin croissant.
    heapq.heappush(
        # Cette file sera consommée avant les prochains démarrages.
        verification_state.scheduled_processes,
        # Le numéro préserve l'ordre d'insertion pour les dates identiques.
        (completion_cycle, verification_state.scheduled_process_count, process),
        # La production reste en attente jusqu'à ce que son cycle soit atteint.
    )


# Chaque entrée passe les mêmes contrôles avant de modifier les stocks.
def _verify_entry(
    # La configuration constitue le catalogue des processus autorisés.
    simulation_config: Config,
    # L'entrée décrit le démarrage à valider.
    trace_entry: TraceEntry,
    # Ce numéro désigne le rang de l'entrée, hors commentaires du fichier.
    entry_number: int,
    # L'état reflète les entrées déjà acceptées dans leur ordre source.
    verification_state: _VerificationState,
    # Les erreurs interrompent le rejeu ; un succès met l'état à jour sur place.
) -> None:
    # La numérotation des diagnostics est distincte des lignes du fichier
    # source.
    """Valide et applique trace_entry, numérotée depuis un par entry_number.

    Lève TraceError pour un cycle décroissant, un processus inconnu ou un
    manque de ressources. Les achèvements antérieurs sont crédités sur place.
    """
    # Revenir en arrière invaliderait la disponibilité calculée des ressources.
    if trace_entry.cycle < verification_state.previous_start_cycle:
        # Le diagnostic présente les deux cycles incompatibles.
        raise TraceError(
            # Le rang repère le démarrage qui rompt la chronologie.
            f"line {entry_number}: cycle {trace_entry.cycle} is before "
            # Le cycle précédent donne la borne minimale autorisée.
            f"cycle {verification_state.previous_start_cycle}"
            # Le rejet intervient avant tout débit de ressources.
        )
    # Les résultats achevés à ce cycle sont disponibles pour ce démarrage.
    completion_cycle = _complete_until(
        # La borne inclut les achèvements simultanés au départ.
        # Le démarrage courant est également un événement temporel.
        trace_entry.cycle,
        # Les opérations terminées seront retirées de la file.
        verification_state.scheduled_processes,
        # Les stocks reçoivent les productions désormais disponibles.
        verification_state.resource_stocks,
        # Le dernier achèvement contribue au temps final du rejeu.
    )
    # Les achèvements peuvent avancer le temps sans entrée supplémentaire.
    verification_state.last_event_cycle = max(
        # La date déjà observée ne doit jamais être diminuée.
        verification_state.last_event_cycle,
        # La fin traitée peut être postérieure au dernier démarrage.
        completion_cycle,
        # Cette borne sera utilisée pour matérialiser le simulateur final.
    )
    # Le nom public de l'entrée désigne une définition du catalogue.
    process = _resolve_process(simulation_config, trace_entry.process)
    # Les déficits sont évalués après les crédits et avant toute consommation.
    missing_quantities = _compute_missing_resources(
        # Les besoins viennent du processus résolu, pas de la trace.
        process,
        # Les stocks consultés incluent les productions déjà terminées.
        verification_state.resource_stocks,
        # Un dictionnaire vide signifie que toutes les ressources sont
        # disponibles.
    )
    # Un seul déficit suffit à rendre le démarrage impossible.
    if missing_quantities:
        # Le diagnostic associe le défaut aux quantités qui permettraient le
        # départ.
        raise TraceError(
            # Le rang et le cycle situent l'échec dans le rejeu.
            f"line {entry_number} at cycle {trace_entry.cycle}: process "
            # Le nom et les déficits précisent les ressources à examiner.
            f"'{process.name}' lacks resources {missing_quantities}"
            # Le rejet empêche toute consommation partielle des besoins.
        )
    # Les contrôles terminés autorisent le débit et la programmation des
    # résultats.
    _consume_and_schedule(trace_entry, process, verification_state)
    # Le prochain démarrage devra respecter cette nouvelle borne chronologique.
    verification_state.previous_start_cycle = trace_entry.cycle
    # Un démarrage tardif compte dans la durée même sans achèvement à cet
    # instant.
    verification_state.last_event_cycle = max(
        # Le maximum conserve le dernier événement effectivement observé.
        verification_state.last_event_cycle,
        # Le démarrage courant est également un événement temporel.
        trace_entry.cycle,
        # Le temps reste ainsi cohérent pour les processus à délai nul.
    )


# Cette fonction adapte l'état du rejeu à l'interface publique Simulator.
def _build_verified_simulator(
    # La configuration fournit les paramètres d'origine du simulateur résultat.
    simulation_config: Config,
    # L'état contient les stocks et opérations de la trace acceptée.
    verification_state: _VerificationState,
    # Le résultat est un simulateur distinct de la configuration source.
) -> Simulator:
    # La borne de finalisation est explicitée plutôt que supposée infinie.
    """Crédite les fins jusqu'à 2**63 - 1 et renvoie l'état validé.

    Modifie verification_state sur place. Les achèvements au-delà de cette
    borne ne sont pas crédités ; cette limite conserve le comportement établi.
    """
    # La borne historique fixe jusqu'où les productions finales sont créditées.
    completion_cycle = _complete_until(
        # Cette valeur est la limite de finalisation, pas une durée de
        # processus.
        2**63 - 1,
        # Les opérations restantes représentent les productions encore
        # attendues.
        verification_state.scheduled_processes,
        # Les crédits finaux complètent les stocks reconstruits.
        verification_state.resource_stocks,
        # La date renvoyée est celle du dernier achèvement traité.
    )
    # La durée doit couvrir les productions après le dernier démarrage.
    verification_state.last_event_cycle = max(
        # L'absence d'achèvement ne doit pas ramener la durée à zéro.
        verification_state.last_event_cycle,
        # La fin traitée peut être postérieure au dernier démarrage.
        completion_cycle,
        # La date retenue servira aux deux champs temporels du simulateur.
    )
    # L'objet standard conserve l'interface attendue par les appelants.
    verified_simulator = Simulator(simulation_config)
    # Le rejeu remplace les stocks initiaux par les quantités réellement
    # obtenues.
    verified_simulator.stocks = verification_state.resource_stocks
    # Le temps public indique la dernière date observée lors de la vérification.
    verified_simulator.time = verification_state.last_event_cycle
    # Le temps maximal doit correspondre au temps reconstruit, comme dans le
    # moteur.
    verified_simulator._max_time = verification_state.last_event_cycle
    # L'appelant reçoit un état directement utilisable pour son compte rendu.
    return verified_simulator


# Cette entrée publique coordonne le rejeu complet d'une trace structurée.
def verify_trace(
    # Les règles du rejeu proviennent de cette configuration.
    simulation_config: Config,
    # La séquence conserve l’ordre demandé, même pour les cycles identiques.
    trace_entries: list[TraceEntry],
    # L’état final est exposé via l’interface du simulateur.
) -> Simulator:
    # Le contrat distingue la faisabilité d'une exigence d'optimalité.
    """Rejoue trace_entries selon simulation_config et renvoie l'état final.

    Les stocks de configuration sont copiés. Les entrées sont traitées dans
    leur ordre fourni, sans tri. Le premier démarrage impossible lève
    TraceError ; une trace réalisable n'a pas à être optimale ni exhaustive.
    """
    # La trace vide nécessite une règle métier propre à l'absence de démarrages.
    if not trace_entries:
        # Le résultat représente alors l'état initial accepté par cette règle.
        return _verify_empty_trace(simulation_config)
    # La copie protège les stocks source contre les débits et crédits du rejeu.
    verification_state = _VerificationState(simulation_config.stocks.copy(), [])
    # Le rang commence à un et conserve l'ordre source des départs simultanés.
    for entry_number, trace_entry in enumerate(trace_entries, start=1):
        # Chaque contrôle s'appuie sur l'état laissé par l'entrée précédente.
        _verify_entry(simulation_config, trace_entry, entry_number, verification_state)
    # Les opérations encore en cours doivent produire avant la restitution
    # finale.
    return _build_verified_simulator(simulation_config, verification_state)


# Cette entrée relie la lecture des fichiers à la vérification métier.
def verify_files(configuration_file_path: Path, trace_file_path: Path) -> Simulator:
    # Les erreurs restent propagées afin que la commande choisisse leur
    # affichage.
    """Lit les deux fichiers et renvoie le simulateur de la trace validée.

    configuration_file_path décrit les stocks, processus et objectifs ;
    trace_file_path décrit les démarrages. Propage les erreurs de lecture,
    ParseError pour la configuration et les erreurs de syntaxe ou de rejeu
    de la trace. Aucun fichier n'est écrit.
    """
    # Le parseur partagé garantit les mêmes règles que la commande de
    # simulation.
    simulation_config = parse_file(configuration_file_path)
    # La syntaxe complète est validée avant la vérification des ressources.
    trace_entries = parse_trace(trace_file_path)
    # Le rejeu structuré fournit le même résultat que l'entrée publique en
    # mémoire.
    return verify_trace(simulation_config, trace_entries)
