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
    parser.add_argument("--log", help="file to write logs to")
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return parser


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

    # Pour centraliser les sorties de logs sans multiplier la configuration.
    handlers: list[logging.Handler] = [logging.StreamHandler()]
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

    # Pour distinguer l'echec de verification d'une simulation valide.
    sim = None
    # Pour centraliser le statut final sans sorties anticipees.
    exit_code = 0
    # Pour convertir une erreur bas niveau en diagnostic exploitable.
    try:
        # Pour deleguer la verification complete a un point unique.
        sim = verify_files(Path(args.config), Path(args.trace))
    # Pour traduire un echec technique en message stable pour l'appelant.
    except ParseError as exc:
        # Pour conserver un diagnostic exploitable dans les logs machine.
        logging.error("invalid config: %s", exc)
        # Pour fournir un retour utilisateur directement lisible en CLI.
        print(f"invalid config: {exc}")
        # Pour centraliser le statut final sans sorties anticipees.
        exit_code = 1
    # Pour traduire un echec technique en message stable pour l'appelant.
    except (OSError, TraceError) as exc:
        # Pour separer clairement les incidents de trace dans l'observabilite.
        logging.error("invalid trace: %s", exc)
        # Pour fournir un retour utilisateur directement lisible en CLI.
        print(f"invalid trace: {exc}")
        # Pour centraliser le statut final sans sorties anticipees.
        exit_code = 1
    # Pour couvrir explicitement le cas complementaire du contrat.
    else:
        # Pour laisser une preuve de succes en mode verbeux.
        logging.info("trace is valid")
        # Pour fournir un retour utilisateur directement lisible en CLI.
        print("trace is valid")

    # Pour traiter explicitement un cas d'entree invalide ou absent.
    if sim is not None:
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
        # Pour fournir un retour utilisateur directement lisible en CLI.
        print(f"Last cycle: {sim.time}")
    # Pour fournir au shell un code retour exploitable en automatisation.
    return exit_code


# Pour proteger un invariant de comparaison critique ici.
if __name__ == "__main__":
    # Pour signaler sans delai une violation explicite du contrat.
    raise SystemExit(main())
