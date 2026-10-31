# Répartition de l'apprentissage — Sylvanna et Rafael

Répartition recalculée le 21 octobre 2026 sur le périmètre conservé,
**sans compter les commentaires ni les docstrings**.

Sylvanna prend les quatre modules métier : parsing, optimisation, simulation
et vérification. Rafael prend tous les autres fichiers du périmètre : les deux
CLI, l'affichage, les initialisations des packages, le Makefile et `pyproject.toml`.
Chaque fichier est attribué en entier à une seule personne. Cette répartition
minimise l'écart de caractères en respectant l'attribution du métier à Sylvanna.

## Périmètre et méthode de comptage

Le périmètre reste celui choisi : tous les fichiers Python de `src/`,
ainsi que `Makefile` et `pyproject.toml`.
Les tests, les autres configurations, la documentation, les ressources et les
artefacts générés sont hors du partage chiffré.

Le comptage mesure des caractères Unicode, et non des octets :

- Python : exclusion des commentaires `# ...` reconnus par `tokenize` et des
  docstrings de modules, classes et fonctions identifiées avec `ast`.
- Makefile et TOML : exclusion des lignes de commentaire commençant par `#`
  après indentation. Les fichiers actuels ne contiennent pas de commentaires
  en fin d'instruction ; cette règle devra être adaptée si cela change.
- Les `#` dans les chaînes, les URL et les messages affichés restent comptés.
- Après retrait de la documentation, les lignes vides et les espaces en fin
  de ligne sont exclus. L'indentation, les espaces internes et un retour à la
  ligne par ligne non vide sont comptés.

Le calcul ne modifie aucun fichier source. Les commentaires restent disponibles
pour apprendre ; seul leur poids dans la répartition est supprimé.

## Bilan

| Personne | Fichiers | Caractères hors commentaires et docstrings | Part du total |
| --- | ---: | ---: | ---: |
| Sylvanna | 4 | 30 600 | 55,96 % |
| Rafael | 7 | 24 082 | 44,04 % |
| **Total** | **11** | **54 682** | **100 %** |

**Écart minimal : 6 518 caractères**, soit 11,92 % du total.
Les 128 attributions possibles des sept fichiers hors métier ont été
comparées, en gardant les quatre modules métier chez Sylvanna.

Un partage à 50/50 représenterait 27 341 caractères par personne.
Les quatre modules métier totalisent déjà 30 600 caractères : Sylvanna
dépasse donc cette moitié de 3 259 caractères. Lui ajouter un
fichier de poids positif augmenterait nécessairement l'écart. Le fichier
`src/krpsim_verif/__init__.py`, de poids nul, reste chez Rafael avec l'autre
initialisation de package ; son attribution ne change pas l'équilibre.
La quantité de code ne mesure pas à elle seule sa difficulté.

## Sylvanna — règles métier

Ordre de lecture conseillé :

| Ordre | Fichier | Caractères | Points à comprendre et expliquer |
| --- | --- | ---: | --- |
| 1 | [src/krpsim/parser.py](../src/krpsim/parser.py) | 6 180 | Modèles `Process` et `Config`, grammaire, validations et erreurs. |
| 2 | [src/krpsim/optimizer.py](../src/krpsim/optimizer.py) | 10 143 | Priorités, dépendances, construction des lots et convertisseur final. |
| 3 | [src/krpsim/simulator.py](../src/krpsim/simulator.py) | 9 334 | Stocks, cycles, démarrages et fins, simultanéité et conditions d'arrêt. |
| 4 | [src/krpsim_verif/verifier.py](../src/krpsim_verif/verifier.py) | 4 943 | Rejeu de la trace, disponibilité des ressources et validité de la chronologie. |
| | **Total Sylvanna** | **30 600** | |

Le vérificateur rejoue la trace fournie : il peut accepter un ordonnancement
valide différent de celui choisi par l'optimiseur.

## Rafael — commandes, affichage et exécution du projet

Ordre de lecture conseillé :

| Ordre | Fichier | Caractères | Points à comprendre et expliquer |
| --- | --- | ---: | --- |
| 1 | [src/krpsim/__init__.py](../src/krpsim/__init__.py) | 113 | API publique et lecture de la version installée. |
| 2 | [src/krpsim_verif/__init__.py](../src/krpsim_verif/__init__.py) | 0 | Rôle du package ; ce fichier contient uniquement une docstring. |
| 3 | [src/krpsim/display.py](../src/krpsim/display.py) | 1 504 | Présentation, formatage et sauvegarde de la trace machine. |
| 4 | [src/krpsim/cli.py](../src/krpsim/cli.py) | 3 182 | Arguments, lancement de la simulation, erreurs et codes de sortie. |
| 5 | [src/krpsim_verif/cli.py](../src/krpsim_verif/cli.py) | 1 466 | Arguments du vérificateur et restitution de son résultat. |
| 6 | [pyproject.toml](../pyproject.toml) | 4 377 | Dépendances, packaging, points d'entrée et configuration des outils qualité. |
| 7 | [Makefile](../Makefile) | 13 440 | Environnement uv, commandes, enchaînement des traitements et nettoyage. |
| | **Total Rafael** | **24 082** | |

## Raccord entre les deux présentations

À réviser ensemble : le format `Config` et `Process`, la trace `cycle:process`,
et les points d'entrée définis dans `pyproject.toml`
qu'appelle le Makefile. Les tests servent de supports pour vérifier les
comportements des fichiers attribués, sans entrer dans les totaux ci-dessus.

## Reproduire le comptage

Depuis la racine du dépôt, copier cette commande dans Bash.
Elle lit les fichiers et affiche leur nombre de caractères selon les règles
ci-dessus, sans les modifier. `wc -m` seul ne retire pas les commentaires.

```bash
python3 - <<'PY'
import ast
import io
import tokenize
from pathlib import Path


def source_without_docs(path):
    source = path.read_text(encoding='utf-8')
    lines = source.splitlines(keepends=True)
    if path.suffix != '.py':
        # Ces deux fichiers ne contiennent actuellement que des commentaires de ligne entière.
        return ''.join(line.rstrip() + '\n' for line in lines
                       if line.strip() and not line.lstrip().startswith('#'))
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def pos(row, col, byte_col=False):
        if byte_col:
            col = len(lines[row - 1].encode('utf-8')[:col].decode('utf-8'))
        return offsets[row - 1] + col

    spans = []
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT:
            spans.append((pos(*tok.start), pos(*tok.end)))
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and ast.get_docstring(node) is not None:
            doc = node.body[0]
            spans.append((pos(doc.lineno, doc.col_offset, True),
                          pos(doc.end_lineno, doc.end_col_offset, True)))
    for start, end in sorted(spans, reverse=True):
        source = source[:start] + source[end:]
    return ''.join(line.rstrip() + '\n' for line in source.splitlines() if line.strip())


if __name__ == '__main__':
    files = sorted(Path('src').rglob('*.py')) + [Path('Makefile'), Path('pyproject.toml')]
    total = 0
    for path in files:
        count = len(source_without_docs(path))
        total += count
        print(f'{count:7} {path}')
    print(f'{total:7} TOTAL')
PY
```

Les nombres sont un instantané : toute modification des fichiers attribués
nécessite un nouveau comptage.
