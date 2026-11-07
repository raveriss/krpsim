# Bilan de validation - 7 novembre 2026

## Document livré

- 52 pages A4 paysage, texte sélectionnable, Inter normal et gras incorporés.
- Repli Noto Sans Arabic incorporé pour le chiffre arabe de l'exemple E24.
- 60 décisions uniques, 181 annotations de liens internes valides.
- Tous les identifiants D01-D60 sont affichés une fois dans les fiches et
  présents dans la matrice CSV. Les questions, conditions et sorties sont
  relues contre le code local ; les boucles et actions sont décrites en complément.
- Les 52 pages de la version finale ont été rendues avec Poppler puis inspectées
  visuellement : pas de texte tronqué, de chevauchement ni de sortie de page
  constaté. Les polices, destinations et limites de page sont également contrôlées
  par `audit_pdf.py`, dont le résultat est dans `pdf_audit.json`.
- Les noms et références Python restent à proximité des questions françaises.
- Les corrections à l'ancien document sont explicitées dans le PDF.
- Aucun test de compréhension auprès d'un lecteur débutant n'a été réalisé.

Le PDF précédent est conservé. Les fichiers du programme et des tests, les seuils
CI, les configurations et le lockfile sont inchangés. Les modifications locales
préexistantes du Makefile et les documents non suivis ont été conservés.

## Exemples exécutés

`verify_examples.py` a exécuté 30 cas sous Python 3.10.20 : E01-E28, EX02 et API01.
Tous donnent le résultat attendu. Les cas acceptés vérifient exactement les stocks
et le dernier cycle ; les cas refusés vérifient le code et le fragment de diagnostic
attendu, selon le cas. E23 et E22 vérifient des exceptions non interceptées.
Le rejeu E04 capture aussi l'état après chacun de ses trois départs.

Les fichiers et observations sont livrés dans `examples/` et
`example_results.json`. Les exemples purement illustratifs des fiches ne sont pas
tous des cas E exécutés ; leur statut et les tests pertinents sont indiqués dans
la matrice. L'inventaire documentaire ne constitue pas une mesure de couverture.

## Environnement et contrôles CI

Configuration examinée : `.github/workflows/ci.yml`, `.pre-commit-config.yaml`,
`pyproject.toml`. Python 3.10.20 a été utilisé, conformément à la série 3.10 de la CI.
Les dépendances ont été installées avec `uv sync --locked --python 3.10` dans un
environnement temporaire, sans remplacer l'environnement de travail existant.

Différences d'environnement : Linux local, pas l'image Ubuntu GitHub Actions ;
uv local 0.12.24 contre 0.11.32 dans le workflow. Le premier `uv run --no-sync`
signale la préférence 3.13 du fichier `.python-version`, mais les journaux confirment
que les tests ont bien tourné en 3.10.20 ; les appels suivants fixent `UV_PYTHON=3.10`.

| Contrôle | Résultat et périmètre |
| --- | --- |
| Ruff `ruff check .` | Réussi sur l'état final, y compris les scripts documentaires. |
| MyPy `mypy src tests` | Réussi, 20 fichiers source. |
| Black `black --check .` | Échec préexistant : `src/krpsim/cli.py` serait reformaté. Les trois scripts livrés passent leur contrôle Black. |
| isort `isort --check-only .` | Réussi. |
| Pre-commit `--all-files` | Exécuté sur copie isolée : Black signale le fichier existant ; isort, flake8, Ruff, MyPy, Bandit, Radon et Xenon passent. |
| Pre-commit des trois scripts livrés | Exécuté séparément sur la copie isolée ; voir `validation/precommit-scripts.log`. |
| Bandit `-r src` | Réussi via le hook, sans désactivation de règle. |
| Radon `cc src --min C` | Réussi via le hook. |
| Xenon `--max-absolute B --max-modules A --max-average A src` | Réussi via le hook, seuils conservés. |
| Pytest avec couverture de branches, dépôt tel quel | 109 réussites, 98 échecs ; couverture combinée 92,01 %, sous le seuil de 100 %. |
| Construction `uv build --no-sources` | Réussie : sdist et wheel. |

Commande de test utilisée, avec les options supplémentaires de `pyproject.toml` :

```bash
uv run --no-sync pytest --cov=krpsim --cov=krpsim_verif --cov-branch \
  --cov-report=xml:coverage.xml --junitxml=junit.xml -o junit_family=legacy
```

Les échecs bruts proviennent des tests qui attendent `resources/simple` et des
chemins équivalents, alors que les fichiers sont dans `resources/good_resources/`
et `resources/bad_resources/`.

Diagnostic complémentaire : dans une copie temporaire, des liens locaux ont
rétabli les anciens chemins, sans changer le dépôt utilisateur. La même commande
donne alors **205 réussites, 2 échecs, 100 % des instructions et des branches**
(887 instructions, 340 branches, aucune manquante). Les deux échecs restants sont :

- `tests/test_partial.py::test_time_cli_saves_and_explains_partial_production[year-50-1]`
- `tests/test_partial.py::test_time_cli_saves_and_explains_partial_production[time;year-500-0]`

Ils attendent le texte « optimalité non garantie », absent du message affiché.
Ces défauts sont hors du périmètre documentaire ; le programme n'a pas été modifié.
Les résultats de la copie de diagnostic ne remplacent pas ceux du dépôt tel quel.

**Le dépôt n'est donc pas déclaré entièrement validé par la CI.** Aucun seuil
n'a été abaissé. Les téléversements Codecov/GitHub, publication PyPI, release et
badge ne sont pas des validations locales de ce document et n'ont pas été lancés.

## Régénération et sources

La mise en page utilise WeasyPrint 70.0 ; l'audit utilise PyMuPDF 1.28.2.
Les fontes Inter 3.19 sont livrées sous leur licence OFL. Ce choix de rendu HTML/CSS
permet d'intégrer les fontes OTF locales, les liens et les schémas vectoriels.

`source_manifest.json` conserve la révision Git et les empreintes SHA-256 des
fichiers analysés et du PDF précédent. `README.md` fournit les commandes de
régénération. Les journaux des contrôles sont livrés dans `validation/`.
