# Validation de la grille KrpSim

Validation locale du 31 octobre 2026, à partir de
« KrpSim — Grille d’évaluation (mise en page).pdf » (deux pages).
Les critères techniques sont reproduits dans `tests/test_evaluation.py`.
Chaque simulation de cette suite est rejouée par `krpsim_verif` : stocks finaux
et date de fin doivent correspondre, sans stock négatif ni dépassement de la
borne donnée à `Simulator.run`.

## Résultats

| Critère | Vérification | Résultat |
| --- | --- | --- |
| Simple | Chaîne complète et durée égale à la somme des processus | 1 client satisfait en 60 cycles |
| Ikea | Répétitions et fabrication simultanée des composants | 1 armoire en 50 cycles, 7 planches consommées |
| Plus compliqué | Ajout d'une branche morte plus rapide, consommant tout le capital de `simple` | Branche évitée, objectif conservé en 60 cycles |
| Steak | Cuisson complète des trois unités | 3 cuits, 0 cru, 0 mi-cuit, poêle restituée au cycle 30 |
| Erreurs de syntaxe | Stocks, processus, ressources et directives mal formés | Rejet CLI avec `invalid config`, code 1 |
| Parties manquantes | Fichier vide, commentaires seuls, absence de stocks ou de processus | Rejet CLI avec `invalid config`, code 1 |
| Vérificateur | Format invalide, processus inconnu, stocks indisponibles, poêle occupée, résultat utilisé trop tôt | Rejet des traces incorrectes et acceptation des traces valides |
| Non-stop / rendement | `recre` à 40, 110 et 500 cycles | Respectivement 2, 3 et 8 marelles |
| Plus gros | `pomme` à 1 000, 10 000 et 50 000 cycles, avec rejeu des traces | Respectivement 6 000, 296 100 et 1 456 550 de bénéfice |
| Bonus indicatif | `pomme` à 50 000 cycles | Seuil de 1 M€ dépassé, correspondant à 5/5 dans cette version de la grille |

Dans `pomme`, `do_benef` convertit les euros en `benefice` : le stock final
`euro` vaut donc zéro. Le score ci-dessus est la valeur de `benefice`.
Le cas à 50 000 cycles comporte 1 474 948 actions et termine au cycle 49 961.

### Distinguer le capital initial de la borne de simulation

Le résultat `No more process doable at time 0`, `benefice => 10000` est
reproductible avec `krpsim resources/pomme 10`. Les achats durent 200 cycles
et aucun ne peut finir dans cette borne de 10 cycles. Le simulateur exécute
donc uniquement la conversion instantanée du capital initial en `benefice`.
Ce résultat n'est pas celui du scénario à 10 000 ou à 50 000 cycles.

Les tests couvrent maintenant aussi la CLI de `pomme`, la trace effectivement
écrite sur disque et son rejeu : production de boîtes, bénéfice supérieur au
capital initial à 10 000 cycles, puis strictement supérieur à 1 M€ à 50 000.
Le test CLI de `steak` vérifie également la trace sauvegardée, les trois steaks
cuits au cycle 30, l'absence de crus et de mi-cuits, et la restitution de la poêle.
Ces résultats sont atteints par l'algorithme déjà présent ; cette vérification
ajoute des protections de non-régression sans modifier sa stratégie.

```bash
make krpsim resources/steak 100
make krpsim_verif resources/steak trace_steak.txt
make krpsim resources/pomme 10000 > pomme_10000.log
make krpsim_verif resources/pomme trace_pomme.txt
make krpsim resources/pomme 50000 > pomme_50000.log
make krpsim_verif resources/pomme trace_pomme.txt
```

La trace de `pomme` est écrasée entre les deux essais ; chaque vérification
doit suivre la simulation correspondante. Les sorties détaillées sont
redirigées vers des journaux pour éviter de saturer l'affichage.

Les points administratifs (présence du groupe, ponctualité, appréciation du
correcteur, flags) restent à vérifier humainement. Les deux commandes sont
présentes, et l'optimisation utilise le code Python du projet sans solveur
externe ni dépendance d'exécution.

## Régression steak et correction

Avant correction, la trace était `cuisson_1`, `cuisson_2`, `cuisson_4` :
2 steaks cuits et 1 mi-cuit au cycle 30. Le planificateur pouvait vérifier un
besoin, puis consommer cette même ressource pour fabriquer un autre besoin.
Il acceptait alors un plan virtuel impossible, qui bloquait son exécution.

Tous les besoins sont maintenant contrôlés ensemble avant leur consommation.
Pour `time`, le classement anticipe jusqu'à trois lots supplémentaires, avec
un budget de 256 candidats par choix initial. Il compare la production
atteignable, puis la durée cumulée et le coût matériel. Les prolongements dont
la durée cumulée dépasse le temps restant ne sont pas valorisés. Le simulateur
conserve les lancements en parallèle et contrôle les dates de fin réelles.
Cette recherche bornée reste heuristique : elle ne prouve pas l'optimalité sur
tous les graphes, et la durée cumulée est une estimation conservatrice quand
plusieurs processus peuvent tourner simultanément.

La nouvelle trace est :

```text
0:cuisson_1
10:cuisson_3
20:cuisson_2
```

Le test couvre aussi 1 à 9 steaks initiaux, des délais insuffisants (notamment
2 steaks cuits en 20 cycles), ainsi que des ressources et processus renommés,
des besoins réordonnés et des durées changées. La correction ne dépend donc
pas des noms de l'exemple. Deux défauts de parsing découverts pendant la
validation sont également corrigés : quantité absente et nom de ressource vide.

## Reproduire

Validation CI locale : Python 3.10.20, uv 0.11.32 comme dans la CI,
dépendances issues de `uv.lock`, 166 tests réussis, couverture des lignes
et des branches à 100 %.
Les hooks pre-commit (Black, isort, Flake8, Ruff, mypy, Bandit, Radon, Xenon),
les commandes d'analyse statique de la CI et la construction du sdist et du
wheel réussissent. Aucun seuil CI n'a été modifié. Les environnements de
validation et de construction ont été isolés de la `.venv` de travail.

```bash
uv sync --locked --python 3.10
UV_PYTHON=3.10 uv run --no-sync krpsim resources/steak 100 --trace trace_steak.txt
UV_PYTHON=3.10 uv run --no-sync krpsim_verif resources/steak trace_steak.txt
UV_PYTHON=3.10 uv run --no-sync pytest tests/test_evaluation.py --no-cov
UV_PYTHON=3.10 uv run --no-sync pytest --cov=krpsim --cov=krpsim_verif --cov-branch \
  --cov-report=xml:coverage.xml --junitxml=junit.xml -o junit_family=legacy
UV_PYTHON=3.10 uv run --no-sync pre-commit run --all-files
UV_PYTHON=3.10 uv run --no-sync ruff check .
UV_PYTHON=3.10 uv run --no-sync mypy src tests
UV_PYTHON=3.10 uv run --no-sync black --check .
UV_PYTHON=3.10 uv run --no-sync isort --check-only .
UV_PYTHON=3.10 uv build --no-sources
```

La CLI existante traite `time` en premier critère avec un horizon interne de
500 cycles, indépendamment du délai saisi. Les tests des bornes courtes passent
donc directement par `Simulator.run`. L'absence de directive `optimize` reste
acceptée par le contrat actuel du parseur.
