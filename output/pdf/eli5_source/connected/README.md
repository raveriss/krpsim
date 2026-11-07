# Arbre de décision relié de krpsim_verif

Le PDF `output/pdf/krpsim_verif_arbre_de_decision_relie.pdf` contient 34 pages :
une couverture, un sommaire cliquable et 32 logigrammes avec 272 nœuds et
304 flèches dessinées. Commencer par G01. Les rectangles à double bord indiquent
un appel ou un sous-parcours détaillé dans le schéma Gxx mentionné. Revenir ensuite
à la sortie de ce rectangle. Les renvois du pied de page sont cliquables.
Les erreurs interrompent le parcours et sont traitées dans G02.

Chaque nœud est accessible depuis le début de son schéma ; tous les schémas sont
accessibles par les renvois depuis G01. Les branches Oui/Non et les retours de boucle
ont des pointes de flèche. Les identifiants Python et les références du code restent
visibles près des étapes. Les 60 identifiants D01-D60 correspondent à la matrice
`../matrice_tracabilite.csv` et aux fiches du guide ELI5 précédent, conservé.
Les exemples, le vocabulaire, les exercices et leurs corrections se trouvent dans
ce guide complémentaire. Le présent PDF se concentre sur les parcours reliés.

## Sources modifiables et régénération

Modifier `graphs.json` pour le contenu et les connexions, `style.css` pour la
présentation, puis exécuter depuis la racine du dépôt :

```bash
uv run --no-project --python 3.10 --with weasyprint==70.0 python output/pdf/eli5_source/connected/build_connected.py
uv run --no-project --python 3.10 --with weasyprint==70.0 --with pymupdf==1.28.2 python output/pdf/eli5_source/connected/audit_connected.py
```

Graphviz (`dot`) et les bibliothèques système de WeasyPrint (Pango notamment)
sont nécessaires. Les fontes Inter sont dans `../fonts/` avec leur licence.
Le script produit les fichiers DOT/SVG, le HTML et le PDF. Les DOT et SVG peuvent
également être ouverts et modifiés séparément ; une nouvelle génération les
remplace à partir de `graphs.json`.

## Vérifications du 7 novembre 2026

- 34 pages rendues en PNG avec Poppler et inspectées visuellement ; contrôle des
  flèches, des libellés, des retours de boucle, des marges et des coupures.
- Audit structurel réussi : connexions, sorties Oui/Non, nœuds accessibles,
  présence des 60 décisions, liens PDF, polices Inter incorporées et texte dans
  les limites des pages. Résultats : `validation.json` et `graph_audit.json`.
- Texte principal des nœuds d’au moins 11 points ; formats A3 paysage et portrait
  choisis selon les schémas pour préserver la lisibilité. Texte sélectionnable et
  traits vectoriels. Les références techniques sont en second niveau.
- Pre-commit des deux scripts réussi sous Python 3.10.20 : Black, isort, flake8,
  Ruff, MyPy, Bandit, Radon et Xenon ; journal `validation-precommit.log`.
- Les 30 exemples du guide donnent les résultats attendus ; sources et résultats
  dans le dossier parent. Aucun test de compréhension auprès d’un débutant.
- Programme et ancien PDF inchangés, empreintes vérifiées avec
  `../source_manifest.json`.

La CI complète du dépôt reste en échec pour des défauts préexistants : chemins de
fixtures des tests, deux attentes de message après rétablissement de ces chemins
dans une copie de diagnostic, et formatage de `src/krpsim/cli.py`.
Le bilan détaillé et les journaux sont dans `../validation.md` et `../validation/`.
La réussite des contrôles documentaires ne signifie pas que toute la CI est verte.
Aucun seuil ni fichier du programme n’a été changé.
