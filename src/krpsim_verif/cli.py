# Ce module relie la commande krpsim_verif à la validation des fichiers.
"""Interface en ligne de commande du vérificateur de traces ``krpsim_verif``.

La commande attend une configuration et une trace au format cycle:processus.
Elle présente le résultat, puis les stocks finaux si la trace est valide.
Les codes de sortie permettent aux scripts appelants de détecter un échec.
"""

# Les annotations décrivent les types sans être évaluées au chargement.
from __future__ import annotations

# argparse prend en charge les arguments obligatoires, l'aide et ses erreurs.
import argparse

# Path représente les chemins dans le format attendu par verify_files.
from pathlib import Path

# ParseError permet d'identifier les erreurs de configuration dans le bilan.
from krpsim.parser import ParseError

# Simulator décrit l'objet contenant les stocks et le cycle après validation.
from krpsim.simulator import Simulator

# La validation et ses erreurs métier restent définies dans le vérificateur.
from .verifier import TraceError, verify_files


# build_parser garde l'interface commune aux deux commandes et à leurs tests.
def build_parser() -> argparse.ArgumentParser:
    """Définit les arguments acceptés par la commande de vérification.

    Paramètres :
        Aucun.

    Retour :
        Analyseur argparse prêt à lire les chemins de configuration et de trace.

    Contrat :
        Le premier argument positionnel devient config, le second devient trace.
        L'option d'aide est fournie par argparse. Aucun fichier n'est lu ici.
    """
    # Le nom présenté dans l'aide reste celui de la commande installée.
    verification_parser = argparse.ArgumentParser(prog="krpsim_verif")
    # Ce premier chemin désigne les stocks et processus de référence.
    verification_parser.add_argument("config", help="configuration file path")
    # Ce second chemin désigne les démarrages de processus à contrôler.
    verification_parser.add_argument("trace", help="execution trace file path")
    # L'appelant peut analyser ses arguments ou consulter l'aide séparément.
    return verification_parser


# Cette fonction traduit la validation métier en bilan de commande.
def _verify_requested_files(
    # Ces attributs config et trace proviennent de l'analyse des arguments.
    verification_arguments: argparse.Namespace,
    # Le couple associe l'état validé au code de sortie attendu par main.
) -> tuple[Simulator | None, int]:
    """Valide les fichiers demandés et présente le résultat de vérification.

    Paramètres :
        verification_arguments: Arguments possédant les attributs config et
            trace, contenant chacun un chemin sous forme de texte.

    Retour :
        Le simulateur validé et le code 0 en cas de succès ; None et le code 1
        si une erreur de configuration, de lecture ou de trace est traitée.

    Contrat :
        Lit les deux fichiers et écrit un message dans la sortie standard.
        Les erreurs ParseError, OSError et TraceError deviennent un code 1.
        Les autres exceptions se propagent à l'appelant.
    """
    # Les erreurs attendues doivent fournir un diagnostic et un code d'échec.
    try:
        # Le texte de config devient le chemin des règles de simulation.
        configuration_file_path = Path(verification_arguments.config)
        # Le texte de trace devient le chemin des événements à valider.
        trace_file_path = Path(verification_arguments.trace)
        # Le même vérificateur assure la lecture et la cohérence de la trace.
        verified_simulator = verify_files(configuration_file_path, trace_file_path)
    # Une configuration invalide nécessite un diagnostic distinct de la trace.
    except ParseError as configuration_error:
        # Le détail conservé aide à retrouver la règle de configuration violée.
        print(f"invalid config: {configuration_error}")
        # Aucun état ne doit être présenté comme validé après cet échec.
        return None, 1
    # Le contrat existant regroupe les erreurs de lecture et de trace.
    except (OSError, TraceError) as trace_verification_error:
        # Le préfixe reste stable ; le détail précise la cause de l'échec.
        print(f"invalid trace: {trace_verification_error}")
        # Le code 1 signale à main que les stocks ne doivent pas être affichés.
        return None, 1
    # Ce message confirme que la lecture et la validation ont toutes réussi.
    print("trace is valid")
    # L'état validé permet d'afficher le bilan, et 0 indique le succès.
    return verified_simulator, 0


# Le format du bilan final est regroupé ici pour faciliter son évolution.
def _print_final_stocks(verified_simulator: Simulator) -> None:
    """Présente les quantités finales et le dernier cycle d'une trace valide.

    Paramètres :
        verified_simulator: Simulateur contenant l'état issu de la validation.

    Retour :
        None. Le bilan est écrit dans la sortie standard.

    Contrat :
        Présente tous les stocks de la configuration dans l'ordre alphabétique,
        avec des quantités alignées et zéro pour un stock absent de l'état final.
        Le simulateur reste inchangé, y compris si aucun stock n'est défini.
    """
    # Le tri rend l'ordre du bilan indépendant de l'ordre de la configuration.
    stock_names = sorted(verified_simulator.config.all_stock_names())
    # Une configuration sans stock conserve une largeur d'affichage nulle.
    stock_name_width = 0
    # Tous les noms contribuent à fixer une largeur commune aux lignes du bilan.
    for stock_name in stock_names:
        # Le nom le plus long détermine où commence la colonne des quantités.
        stock_name_width = max(stock_name_width, len(stock_name))
    # Cet en-tête sépare les quantités du message de validation précédent.
    print("Final Stocks:")
    # Chaque stock déclaré apparaît, même si sa quantité finale est nulle.
    for stock_name in stock_names:
        # Une ressource absente des stocks a une quantité nulle.
        final_stock_quantity = verified_simulator.stocks.get(stock_name, 0)
        # Le symbole < complète le nom à droite pour aligner les quantités.
        aligned_stock_name = f"{stock_name:<{stock_name_width}}"
        # L'indentation et la flèche conservent le format du bilan existant.
        print(f"  {aligned_stock_name}  => {final_stock_quantity}")
    # Ce cycle inclut les dernières productions terminées pendant la validation.
    print(f"Last cycle: {verified_simulator.time}")


# Le nom main conserve le point d'entrée déclaré dans pyproject.toml.
def main(command_line_arguments: list[str] | None = None) -> int:
    """Valide une trace et présente son état final en ligne de commande.

    Paramètres :
        command_line_arguments: Arguments sans le nom du programme.
            Si None, utilise les arguments fournis dans le terminal.

    Retour :
        ``0`` si la trace est valide, ``1`` si une erreur de configuration,
        de lecture de fichier ou de trace est traitée.

    Exceptions :
        SystemExit: Code ``0`` pour l'aide, ``2`` pour des arguments invalides.

    Contrat :
        Attend le chemin de configuration puis celui de la trace.
        Écrit le résultat de vérification dans la sortie standard ;
        les stocks finaux et le dernier cycle ne suivent qu'en cas de succès.
    """
    # La définition des arguments reste partagée avec l'aide et les tests.
    verification_parser = build_parser()
    # parse_args associe les arguments aux chemins config et trace ;
    # une liste explicite permet un appel sans dépendre du terminal.
    verification_arguments = verification_parser.parse_args(command_line_arguments)
    # Cette étape valide les fichiers et traduit les erreurs prises en charge
    # en message lisible et en code de sortie pour l'appelant.
    verified_simulator, verification_exit_code = _verify_requested_files(
        # Les deux chemins analysés désignent les fichiers à contrôler.
        verification_arguments
        # Le bilan n'utilise l'état renvoyé que si la validation a réussi.
    )
    # Un échec ne fournit aucun simulateur dont les stocks seraient validés.
    if verified_simulator is not None:
        # Le bilan décrit les stocks et le dernier cycle de la trace validée.
        _print_final_stocks(verified_simulator)
    # Ce code permet à la commande appelante de distinguer succès et échec.
    return verification_exit_code


# L'import du module doit rester sans effet ; seul son lancement appelle main.
if __name__ == "__main__":
    # SystemExit transmet le succès ou l'échec au programme appelant.
    raise SystemExit(main())
