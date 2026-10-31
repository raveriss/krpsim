"""Interface CLI du verificateur de trace ``krpsim_verif``.

Ce module valide une trace produite par le simulateur et expose des codes
retour stables pour les chaines d'automatisation.
"""

# Pour retarder l'evaluation des types et limiter les cycles.
from __future__ import annotations

# Pour stabiliser l'interface CLI et ses erreurs utilisateur.
import argparse

# Pour eviter les chemins fragiles relies aux separateurs OS.
from pathlib import Path

# Pour reutiliser la logique canonique du simulateur sans duplication.
from krpsim.parser import ParseError
from krpsim.simulator import Simulator

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
    # Pour rendre a l'appelant le resultat promis par le contrat.
    return parser


def _verify_inputs(args: argparse.Namespace) -> tuple[Simulator | None, int]:
    """Run verification and print its stable error messages."""
    try:
        sim = verify_files(Path(args.config), Path(args.trace))
    except ParseError as exc:
        print(f"invalid config: {exc}")
        return None, 1
    except (OSError, TraceError) as exc:
        print(f"invalid trace: {exc}")
        return None, 1
    print("trace is valid")
    return sim, 0


def _print_final_stocks(sim: Simulator) -> None:
    """Print the final stock snapshot for a successful verification."""
    stock_names = sorted(sim.config.all_stock_names())
    max_len = max((len(name) for name in stock_names), default=0)
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

    sim, exit_code = _verify_inputs(args)

    # Pour traiter explicitement un cas d'entree invalide ou absent.
    if sim is not None:
        _print_final_stocks(sim)
    # Pour fournir au shell un code retour exploitable en automatisation.
    return exit_code


# Pour proteger un invariant de comparaison critique ici.
if __name__ == "__main__":
    # Pour signaler sans delai une violation explicite du contrat.
    raise SystemExit(main())
