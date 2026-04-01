"""Analyseur de configuration KRPSIM.

Ce module convertit le fichier texte en objets structures et applique les
contraintes de validite necessaires a une simulation fiable.
"""

# Pour retarder l'evaluation des types et limiter les cycles.
from __future__ import annotations

# Pour appliquer des verifications d'acces dependantes du systeme.
import os
# Pour imposer une grammaire stricte via des motifs explicites.
import re
# Pour formaliser des contrats de donnees clairs et compacts.
from dataclasses import dataclass
# Pour eviter les chemins fragiles relies aux separateurs OS.
from pathlib import Path

# Pour detecter un encodage interdit avant toute interpretation.
UTF8_BOM = b"\xef\xbb\xbf"


# Pour fiabiliser les objets metier via un schema declaratif.
@dataclass
# Pour encapsuler Process autour d'un contrat clairement borne.
class Process:
    """Represente un processus executable par le simulateur.

    Attributes:
        name: Identifiant unique du processus.
        needs: Ressources consommees au demarrage.
        results: Ressources produites a la fin.
        delay: Duree de production exprimee en cycles.

    Contrat:
        Les quantites sont supposees valides et non negatives apres parsing.
    """

    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    name: str
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    needs: dict[str, int]
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    results: dict[str, int]
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    delay: int


# Pour fiabiliser les objets metier via un schema declaratif.
@dataclass
# Pour encapsuler Config autour d'un contrat clairement borne.
class Config:
    """Represente une configuration complete prete a simuler.

    Attributes:
        stocks: Stocks initiaux declares dans le fichier.
        processes: Processus indexés par nom pour acces direct.
        optimize: Criteres d'optimisation optionnels.

    Contrat:
        Les dictionnaires ne contiennent pas de doublons de noms.
    """

    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    stocks: dict[str, int]
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    processes: dict[str, Process]
    # Pour representer explicitement l'absence de critere d'optimisation.
    optimize: list[str] | None = None

    # Pour isoler all_stock_names et faciliter son evolution sous tests.
    def all_stock_names(self) -> set[str]:
        """Retourne toutes les ressources mentionnees dans la config.

        Parameters:
            Aucun parametre.

        Returns:
            Ensemble des noms vus en stock initial, besoins et resultats.

        Raises:
            Aucune exception n'est levee explicitement.

        Contrat:
            L'ensemble retourne doit etre exhaustif pour fiabiliser les
            verifications d'affichage et d'optimisation.
        """
        # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
        names: set[str] = set(self.stocks)
        # Pour appliquer uniformement la regle a chaque element concerne.
        for process in self.processes.values():
            # Pour inclure les ressources consommees dans l'inventaire complet.
            names.update(process.needs)
            # Pour inclure les ressources produites dans l'inventaire complet.
            names.update(process.results)
        # Pour rendre a l'appelant le resultat promis par le contrat.
        return names


# Pour encapsuler ParseError autour d'un contrat clairement borne.
class ParseError(Exception):
    """Signale une configuration invalide selon le contrat KRPSIM."""


# Pour isoler _parse_stock et faciliter son evolution sous tests.
def _parse_stock(line: str) -> tuple[str, int]:
    """Parse une ligne de stock ``nom:quantite``.

    Parameters:
        line: Ligne brute provenant du fichier de configuration.

    Returns:
        Tuple ``(nom, quantite)`` valide.

    Raises:
        ParseError:
            Si la ligne ne respecte pas le format attendu.

    Contrat:
        Les erreurs doivent rester explicites pour faciliter le diagnostic
        utilisateur sur des fichiers de configuration volumineux.
    """
    # Pour convertir une erreur bas niveau en diagnostic exploitable.
    try:
        # Pour isoler une etape de validation et garder un diagnostic clair.
        name, qty = line.split(":", 1)
    # Pour traduire un echec technique en message stable pour l'appelant.
    except ValueError as exc:
        # Pour signaler sans delai une violation explicite du contrat.
        raise ParseError(f"invalid stock line: '{line}'") from exc
    # Pour traiter explicitement un cas d'entree invalide ou absent.
    if not name or not qty.isdigit():
        # Pour signaler sans delai une violation explicite du contrat.
        raise ParseError(f"invalid stock line: '{line}'")
    # Pour verrouiller les calculs suivants sur un type numerique fiable.
    quantity = int(qty)
    # Pour expliciter une decision qui impacte le flux metier.
    if quantity < 0:
        # Pour signaler sans delai une violation explicite du contrat.
        raise ParseError(f"invalid stock quantity in line: '{line}'")
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return name, quantity


# Pour isoler _parse_resources et faciliter son evolution sous tests.
def _parse_resources(block: str) -> dict[str, int]:
    """Parse un bloc de ressources ``nom:qte;nom:qte``.

    Parameters:
        block: Contenu brut d'un bloc ``(...)`` de besoins/resultats.

    Returns:
        Dictionnaire ``ressource -> quantite`` sans doublon.

    Raises:
        ParseError:
            Si une quantite est invalide ou si un nom est duplique.

    Contrat:
        Les quantites de ressources de processus doivent rester strictement
        positives pour eviter des effets de bord non definis en simulation.
    """
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    resources: dict[str, int] = {}
    # Pour traiter explicitement un cas d'entree invalide ou absent.
    if not block:
        # Pour rendre a l'appelant le resultat promis par le contrat.
        return resources
    # Pour appliquer uniformement la regle a chaque element concerne.
    for item in block.split(";"):
        # Pour tolerer des separateurs superflus sans corrompre le parsing.
        if not item:
            # Pour ignorer ce cas et laisser la boucle traiter les suivants.
            continue
        # Pour isoler une etape de validation et garder un diagnostic clair.
        name, qty = item.split(":", 1)
        # Pour traiter explicitement un cas d'entree invalide ou absent.
        if not qty.isdigit():
            # Pour signaler sans delai une violation explicite du contrat.
            raise ParseError(f"invalid quantity for resource '{item}'")
        # Pour verrouiller les calculs suivants sur un type numerique fiable.
        quantity = int(qty)
        # Pour proteger un invariant de comparaison critique ici.
        if quantity <= 0:
            # Pour signaler sans delai une violation explicite du contrat.
            raise ParseError(f"invalid quantity for resource '{item}'")
        # Pour expliciter une decision qui impacte le flux metier.
        if name in resources:
            # Pour signaler sans delai une violation explicite du contrat.
            raise ParseError(f"duplicate resource '{name}' in '{block}'")
        # Pour figer la quantite validee associee a cette ressource.
        resources[name] = quantity
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return resources


# Pour isoler _parse_process et faciliter son evolution sous tests.
def _parse_process(line: str) -> Process:
    """Parse une ligne de processus ``name:(needs):(results):delay``.

    Parameters:
        line: Ligne brute representant un processus.

    Returns:
        Instance ``Process`` validee syntaxiquement.

    Raises:
        ParseError:
            Si la syntaxe de ligne est invalide.

    Contrat:
        Le bloc ``results`` peut etre omis via ``::delay`` pour garder une
        grammaire compacte tout en restant explicite.
    """
    # Pour imposer une validation syntaxique deterministe et compacte.
    match = re.match(r"^([^:]+):\(([^)]*)\):(?:\(([^)]*)\))?:(\d+)$", line)
    # Pour rejeter immediatement une ligne qui viole la grammaire.
    if not match:
        # Pour signaler sans delai une violation explicite du contrat.
        raise ParseError(f"invalid process line: '{line}'")
    # Pour isoler une etape de validation et garder un diagnostic clair.
    name, needs_block, results_block, delay_str = match.groups()
    # Pour verrouiller les calculs suivants sur un type numerique fiable.
    delay = int(delay_str)
    # Pour traiter explicitement un cas d'entree invalide ou absent.
    if delay <= 0:
        # Pour signaler sans delai une violation explicite du contrat.
        raise ParseError(
            f"invalid delay for process '{name}': {delay}. "
            "Delay must be >= 1 cycle. "
            "Action: replace ':0' by a positive delay such as ':1'."
        )
    # Pour partager la meme validation entre besoins et resultats.
    needs = _parse_resources(needs_block)
    # Pour unifier la logique avec le cas de bloc resultat absent.
    results = _parse_resources(results_block or "")
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return Process(
        # Pour construire un objet Process coherant avec les valeurs validees.
        name=name,
        # Pour construire un objet Process coherant avec les valeurs validees.
        needs=needs,
        # Pour construire un objet Process coherant avec les valeurs validees.
        results=results,
        # Pour construire un objet Process coherant avec les valeurs validees.
        delay=delay,
    # Pour clore le bloc sans ambiguite de structure.
    )


# Pour isoler _parse_optimize et faciliter son evolution sous tests.
def _parse_optimize(line: str) -> list[str]:
    """Parse la ligne ``optimize:(...)``.

    Parameters:
        line: Ligne brute de configuration d'optimisation.

    Returns:
        Liste ordonnee des cibles d'optimisation.

    Raises:
        ParseError:
            Si la ligne est vide, mal formee ou contient des doublons.

    Contrat:
        L'ordre des cibles est preserve car il influence la priorisation.
    """
    # Pour imposer une validation syntaxique deterministe et compacte.
    match = re.match(r"^optimize:\(([^)]*)\)$", line)
    # Pour rejeter immediatement une ligne qui viole la grammaire.
    if not match:
        # Pour signaler sans delai une violation explicite du contrat.
        raise ParseError(f"invalid optimize line: '{line}'")
    # Pour isoler une etape de validation et garder un diagnostic clair.
    block = match.group(1)
    # Pour isoler une etape de validation et garder un diagnostic clair.
    items = [item for item in block.split(";") if item]
    # Pour tolerer des separateurs superflus sans corrompre le parsing.
    if not items:
        # Pour signaler sans delai une violation explicite du contrat.
        raise ParseError(f"invalid optimize line: '{line}'")
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    seen: set[str] = set()
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    result: list[str] = []
    # Pour appliquer uniformement la regle a chaque element concerne.
    for item in items:
        # Pour expliciter une decision qui impacte le flux metier.
        if item in seen:
            # Pour signaler sans delai une violation explicite du contrat.
            raise ParseError(f"duplicate optimize target '{item}'")
        # Pour memoire des cibles deja vues et bloquer les doublons.
        seen.add(item)
        # Pour preserver l'ordre de priorite defini dans le fichier.
        result.append(item)
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return result


# Pour isoler _handle_optimize et faciliter son evolution sous tests.
def _handle_optimize(line: str, optimize: list[str] | None) -> list[str] | None:
    """Injecte la section ``optimize`` en interdisant les duplications.

    Parameters:
        line: Ligne ``optimize`` a parser.
        optimize: Etat courant de la section deja rencontree.

    Returns:
        La liste optimisee parsee ou ``None``.

    Raises:
        ParseError:
            Si plusieurs lignes ``optimize`` sont presentes.

    Contrat:
        Une seule declaration ``optimize`` est autorisee par fichier.
    """
    # Pour appliquer la logique specifique au mode optimisation.
    if optimize is not None:
        # Pour signaler sans delai une violation explicite du contrat.
        raise ParseError("duplicate optimize line")
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return _parse_optimize(line)


# Pour isoler _handle_process et faciliter son evolution sous tests.
def _handle_process(line: str, processes: dict[str, Process]) -> None:
    """Ajoute un processus en garantissant l'unicite de son nom.

    Parameters:
        line: Ligne brute de processus.
        processes: Dictionnaire de destination des processus.

    Returns:
        ``None``.

    Raises:
        ParseError:
            Si le nom de processus est deja present.

    Contrat:
        Les noms de processus servent de cle primaire dans la simulation.
    """
    # Pour isoler une etape de validation et garder un diagnostic clair.
    process = _parse_process(line)
    # Pour expliciter une decision qui impacte le flux metier.
    if process.name in processes:
        # Pour signaler sans delai une violation explicite du contrat.
        raise ParseError(f"duplicate process '{process.name}'")
    # Pour indexer les processus par nom et simplifier les acces futurs.
    processes[process.name] = process


# Pour isoler _handle_stock et faciliter son evolution sous tests.
def _handle_stock(line: str, stocks: dict[str, int]) -> None:
    """Ajoute un stock initial en garantissant l'unicite du nom.

    Parameters:
        line: Ligne brute de stock.
        stocks: Dictionnaire de destination des stocks.

    Returns:
        ``None``.

    Raises:
        ParseError:
            Si un stock duplique est detecte.

    Contrat:
        Chaque ressource initiale doit avoir une valeur unique et stable.
    """
    # Pour isoler une etape de validation et garder un diagnostic clair.
    name, qty = _parse_stock(line)
    # Pour expliciter une decision qui impacte le flux metier.
    if name in stocks:
        # Pour signaler sans delai une violation explicite du contrat.
        raise ParseError(f"duplicate stock '{name}'")
    # Pour memoriser une valeur initiale unique par ressource.
    stocks[name] = qty


# Pour isoler _validate_optimize et faciliter son evolution sous tests.
def _validate_optimize(
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    optimize: list[str], stocks: dict[str, int], processes: dict[str, Process]
# Pour ouvrir un bloc qui porte une contrainte locale explicite.
) -> None:
    """Verifie que les cibles ``optimize`` existent dans le modele.

    Parameters:
        optimize: Cibles demandees dans la configuration.
        stocks: Stocks initiaux declares.
        processes: Processus connus et leurs ressources.

    Returns:
        ``None``.

    Raises:
        ParseError:
            Si une cible inconnue autre que ``time`` est demandee.

    Contrat:
        Les criteres d'optimisation doivent toujours correspondre a une
        ressource reelle pour eviter des priorites fantomes.
    """
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    known: set[str] = set(stocks)
    # Pour appliquer les invariants a l'ensemble des processus connus.
    for proc in processes.values():
        # Pour isoler une etape de validation et garder un diagnostic clair.
        known.update(proc.needs)
        # Pour isoler une etape de validation et garder un diagnostic clair.
        known.update(proc.results)
    # Pour appliquer uniformement la regle a chaque element concerne.
    for item in optimize:
        # Pour traiter explicitement un cas d'entree invalide ou absent.
        if item != "time" and item not in known:
            # Pour signaler sans delai une violation explicite du contrat.
            raise ParseError(f"unknown stock '{item}' in optimize line")


# Pour isoler _validate_process_resources et faciliter son evolution sous tests.
def _validate_process_resources(
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    stocks: dict[str, int], processes: dict[str, Process]
# Pour ouvrir un bloc qui porte une contrainte locale explicite.
) -> None:
    """Garantit que tous les besoins de processus sont resolvables.

    Parameters:
        stocks: Stocks initiaux disponibles.
        processes: Processus definis dans la configuration.

    Returns:
        ``None``.

    Raises:
        ParseError:
            Si un processus consomme une ressource jamais definie.

    Contrat:
        Une ressource est consideree definie si elle existe au depart ou peut
        etre produite par au moins un processus.
    """
    # Pour fiabiliser les controles d'unicite et de coherence globale.
    defined = set(stocks)
    # Pour appliquer les invariants a l'ensemble des processus connus.
    for proc in processes.values():
        # Pour isoler une etape de validation et garder un diagnostic clair.
        defined.update(proc.results)
    # Pour appliquer les invariants a l'ensemble des processus connus.
    for proc in processes.values():
        # Pour appliquer uniformement la regle a chaque element concerne.
        for res in proc.needs:
            # Pour traiter explicitement un cas d'entree invalide ou absent.
            if res not in defined:
                # Pour signaler sans delai une violation explicite du contrat.
                raise ParseError(
                    # Pour inclure le processus fautif dans le diagnostic
                    # utilisateur.
                    f"unknown resource '{res}' used in process '{proc.name}'"
                # Pour clore le bloc sans ambiguite de structure.
                )


# Pour isoler _read_lines et faciliter son evolution sous tests.
def _read_lines(path: Path) -> list[str]:
    """Lit un fichier de config en imposant les contraintes d'encodage.

    Parameters:
        path: Chemin du fichier a analyser.

    Returns:
        Lignes lues dans l'ordre d'origine.

    Raises:
        ParseError:
            Si le fichier viole les contraintes d'encodage ou de longueur.
        OSError:
            Si la lecture disque echoue.

    Contrat:
        Les rejets d'encodage sont precoces pour eviter des diagnostics
        trompeurs plus tard dans le parsing semantique.
    """
    # Pour controler BOM et fins de ligne avant decodage UTF-8.
    raw = path.read_bytes()
    # Pour expliciter une decision qui impacte le flux metier.
    if raw.startswith(UTF8_BOM):
        # Pour signaler sans delai une violation explicite du contrat.
        raise ParseError("BOM detected in file")
    # Pour convertir une erreur bas niveau en diagnostic exploitable.
    try:
        # Pour normaliser l'encodage et fiabiliser les diagnostics de parsing.
        text = raw.decode("utf-8")
    # Pour traduire un echec technique en message stable pour l'appelant.
    except UnicodeDecodeError as exc:
        # Pour signaler sans delai une violation explicite du contrat.
        raise ParseError("file must be UTF-8 encoded") from exc
    # Pour expliciter une decision qui impacte le flux metier.
    if b"\r" in raw:
        # Pour signaler sans delai une violation explicite du contrat.
        raise ParseError("CRLF line endings are not allowed")
    # Pour conserver la notion de ligne utile aux messages d'erreur.
    lines = text.splitlines()
    # Pour valider chaque ligne avec le meme niveau d'exigence.
    for raw_line in lines:
        # Pour expliciter une decision qui impacte le flux metier.
        if len(raw_line) > 255:
            # Pour signaler sans delai une violation explicite du contrat.
            raise ParseError("line exceeds 255 characters")
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return lines


# Pour isoler _parse_lines et faciliter son evolution sous tests.
def _parse_lines(
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    lines: list[str],
# Pour ouvrir un bloc qui porte une contrainte locale explicite.
) -> tuple[dict[str, int], dict[str, Process], list[str] | None]:
    """Parse les lignes valides en structures metier.

    Parameters:
        lines: Lignes prealablement lues et decodees.

    Returns:
        Tuple ``(stocks, processes, optimize)``.

    Raises:
        ParseError:
            Si une ligne ne correspond a aucun format autorise.

    Contrat:
        Les commentaires et lignes vides sont ignores pour faciliter
        l'edition manuelle des configurations.
    """
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    stocks: dict[str, int] = {}
    # Pour typer explicitement le champ et fiabiliser le contrat de donnees.
    processes: dict[str, Process] = {}
    # Pour representer explicitement l'absence de critere d'optimisation.
    optimize: list[str] | None = None

    # Pour valider chaque ligne avec le meme niveau d'exigence.
    for line in lines:
        # Pour neutraliser les espaces parasites en edition manuelle.
        line = line.strip()
        # Pour traiter explicitement un cas d'entree invalide ou absent.
        if not line or line.startswith("#"):
            # Pour ignorer ce cas et laisser la boucle traiter les suivants.
            continue
        # Pour appliquer la logique specifique au mode optimisation.
        if line.startswith("optimize:"):
            # Pour separer explicitement les etats intermediaires du traitement.
            optimize = _handle_optimize(line, optimize)
        # Pour maintenir un ordre de priorite stable entre cas exclusifs.
        elif ":(" in line:
            # Pour appliquer la validation dediee aux lignes processus.
            _handle_process(line, processes)
        # Pour maintenir un ordre de priorite stable entre cas exclusifs.
        elif ":" in line:
            # Pour appliquer la validation dediee aux lignes stock.
            _handle_stock(line, stocks)
        # Pour couvrir explicitement le cas complementaire du contrat.
        else:
            # Pour signaler sans delai une violation explicite du contrat.
            raise ParseError(f"unrecognized line: '{line}'")
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return stocks, processes, optimize


# Pour isoler parse_file et faciliter son evolution sous tests.
def parse_file(path: Path) -> Config:
    """Parse un fichier de configuration complet.

    Parameters:
        path: Chemin du fichier de configuration a parser.

    Returns:
        Une instance ``Config`` prete a etre simulee.

    Raises:
        ParseError:
            Si le chemin ou le contenu viole le contrat attendu.

    Contrat:
        La configuration finale doit contenir au moins un stock et un
        processus, sans reference de ressources inconnues.
    """
    # Pour bloquer la traversal de chemin hors perimetre attendu.
    if ".." in path.parts:
        # Pour signaler sans delai une violation explicite du contrat.
        raise ParseError("path traversal detected")
    # Pour echouer tot quand la cible n'est pas un fichier valide.
    if not path.is_file():
        # Pour signaler sans delai une violation explicite du contrat.
        raise ParseError(f"invalid path: '{path}'")
    # Pour detecter un probleme de permission avant l'execution metier.
    if not os.access(path, os.R_OK):
        # Pour signaler sans delai une violation explicite du contrat.
        raise ParseError(f"file is not readable: '{path}'")

    # Pour separer lecture brute et validation metier de la configuration.
    lines = _read_lines(path)
    # Pour separer lecture brute et validation metier de la configuration.
    stocks, processes, optimize = _parse_lines(lines)
    # Pour traiter explicitement un cas d'entree invalide ou absent.
    if not stocks or not processes:
        # Pour signaler sans delai une violation explicite du contrat.
        raise ParseError("configuration must define at least one stock and process")
    # Pour appliquer la logique specifique au mode optimisation.
    if optimize:
        # Pour verifier les cibles avant lancement de la simulation.
        _validate_optimize(optimize, stocks, processes)
    # Pour rejeter toute ressource requise mais jamais definie.
    _validate_process_resources(stocks, processes)
    # Pour livrer une configuration validee prete a simuler.
    return Config(stocks=stocks, processes=processes, optimize=optimize)
