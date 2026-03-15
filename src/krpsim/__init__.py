"""Surface publique minimale du package ``krpsim``.

Ce module centralise les symboles considérés stables pour les appels
externes afin de limiter les couplages aux détails internes.
"""

# Pour lire la version installee depuis la source officielle.
from importlib import metadata

# Pour limiter l'API publique et reduire les couplages externes.
__all__ = ["version"]


# Pour isoler version et faciliter son evolution sous tests.
def version() -> str:
    """Expose la version installée du package.

    Parameters:
        Aucun paramètre.

    Returns:
        La version normalisée fournie par les métadonnées installées.

    Raises:
        importlib.metadata.PackageNotFoundError:
            Si le package n'est pas installé dans l'environnement courant.

    Contrat:
        Cette fonction reflète l'état réel de l'installation active et
        ne dépend pas d'une constante codée en dur.
    """
    # Pour exposer la version effective de l'installation active.
    return metadata.version("krpsim")
