# ⏱️ Production Process Simulator & Verifier (Python) - KRPSIM

<div align="center">

[![CI](https://img.shields.io/github/actions/workflow/status/raveriss/krpsim/ci.yml?branch=main&logo=githubactions&logoColor=white)](https://github.com/raveriss/krpsim/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/codecov/c/github/raveriss/krpsim?logo=codecov&logoColor=white)](https://codecov.io/gh/raveriss/krpsim)
![pre-commit](https://img.shields.io/badge/pre--commit-enabled-FAB040?logo=precommit&logoColor=white)
![Python](https://img.shields.io/badge/Python-%3E%3D3.10%2C%3C3.14-3776AB?logo=python&logoColor=white)
[![uv](https://img.shields.io/badge/uv-project%20manager-DE5FE9?logo=uv&logoColor=white)](https://docs.astral.sh/uv/)
![Ruff](https://img.shields.io/badge/Ruff-lint-46A35E?logo=ruff&logoColor=white)
![MyPy](https://img.shields.io/badge/MyPy-types-2A6DB2?logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI%2BPHBhdGggZmlsbD0iI2ZmZmZmZiIgZD0iTTMgMTlWNWgzLjJMMTIgMTIuNCAxNy44IDVIMjF2MTRoLTNWMTAuMWwtNC44IDYuMUgxMC44TDYgMTAuMVYxOXoiLz48L3N2Zz4%3D)
![License](https://img.shields.io/github/license/raveriss/krpsim?logo=github&logoColor=white)

</div>

##### Ce projet fait partie de mon [`🔗 PORTFOLIO`](https://raveriss.dev/) orienté **Data / IA / Software Engineering**

KRPSIM est un simulateur d'ordonnancement de processus avec vérification de trace. Le projet lit une configuration de stocks/processus, calcule une exécution optimisée et permet de vérifier la cohérence d'une trace d'exécution.

## 🧭 Table des matières

- [🎯 Objectif du projet](#objectif-du-projet)
- [🧩 Fonctionnalités principales](#fonctionnalités-principales)
- [🧰 Stack](#stack)
- [⚙️ Installation (source)](#installation-source)
- [🚀 Quick Start](#quick-start)
- [📋 Tableau des commandes make](#tableau-des-commandes-make)
- [📝 Formats d'entrée](#formats-entree)
- [🖥️ Exemple de sortie: simulation](#exemple-de-sortie-simulation)
- [✅ Exemple de sortie: vérification](#exemple-de-sortie-vérification)
- [🗂️ Structure du projet](#structure-du-projet)
- [🧪 Tests](#tests)
- [🔍 Qualité du code](#qualite-du-code)
- [📚 Documentation](#documentation)
- [👥 Auteurs](#auteurs)
- [🛡️ Licence](#licence)

## 🎯 Objectif du projet

Projet réalisé dans le cadre du cursus **École 42** (projet KRPSIM), avec un objectif d'ingénierie logicielle: parser une grammaire métier, ordonnancer des processus de façon déterministe et valider les sorties.

## 🧩 Fonctionnalités principales

- Simulation d'un flux de production à ressources contraintes.
- Optimisation multi-critères (temps, stock cible).
- Vérification automatique d'une trace (auditabilité d'exécution).

## 🧰 Stack

- **Langage & packaging** : Python `>=3.10,<3.14`, uv, Hatchling
- **Runtime** : bibliothèque standard Python uniquement
- **Tests** : pytest, pytest-cov, Hypothesis
- **Qualité** : Ruff, MyPy, Black, isort, pre-commit

## ⚙️ Installation (source)

```bash
git clone https://github.com/raveriss/krpsim.git
cd krpsim
curl -LsSf https://astral.sh/uv/install.sh | sh
make install
```

Python `3.13` est la version de développement recommandée et elle est déclarée dans
`.python-version`. Le projet reste compatible avec Python `>=3.10,<3.14`. Lors de la
synchronisation, uv utilise cette version et peut la télécharger si elle n'est pas
encore disponible.

Pour installer explicitement l'interpréteur avant la synchronisation :

```bash
uv python install 3.13
make install
```

`make install` vérifie la présence de uv, crée `.venv` et synchronise exactement les
dépendances verrouillées dans `uv.lock`. La commande `make` effectue cette même
installation locale au projet, sans écrire dans `~/.local/bin`. La cible facultative
`make install-bin` permet d'exposer explicitement `krpsim` et `krpsim_verif` dans
`~/.local/bin`. Les autres cibles Make exécutent les outils dans cet environnement ;
vous pouvez donc lancer directement `make krpsim ...`, `make krpsim_verif ...` ou
`make test`.
`make shell` ouvre un shell interactif dans le virtualenv pour le debug manuel et
`make doctor` contrôle uv, Python, le lockfile et l'environnement.

### Utilisation directe de uv

Le même environnement peut être synchronisé et utilisé sans Make :

```bash
uv sync --locked
uv run --locked krpsim resources/ikea 10
uv run --locked krpsim_verif resources/ikea trace_ikea.txt
uv run --locked pytest
```

L'option `--locked` garantit que ces commandes n'altèrent pas `uv.lock` et échoue si
le lockfile n'est plus cohérent avec `pyproject.toml`.

## 🚀 Quick Start

```bash
make krpsim resources/ikea 10
make krpsim_verif resources/ikea trace_ikea.txt
```

### Steak et bonus de rendement

```bash
make krpsim resources/steak 100
make krpsim_verif resources/steak trace_steak.txt
make krpsim resources/pomme 10000 > pomme_10000.log
make krpsim_verif resources/pomme trace_pomme.txt
make krpsim resources/pomme 50000 > pomme_50000.log
make krpsim_verif resources/pomme trace_pomme.txt
```

Résultats vérifiés avec les ressources fournies : trois steaks cuits en 30 cycles,
296 100 de `benefice` pour `pomme` à 10 000 cycles et 1 456 550 à 50 000 cycles.
Ce dernier résultat dépasse le seuil indicatif de 1 M€ du bonus 5/5.
La trace `trace_pomme.txt` est remplacée à chaque exécution : vérifiez-la avant
de lancer le cas suivant. Les journaux évitent d'afficher les nombreuses actions
de conversion finale dans le terminal.

Le dernier argument est une **borne en cycles**, pas une durée CPU en secondes.
Avec `pomme 10`, les achats de 200 cycles ne peuvent pas démarrer : seul
`do_benef` convertit le capital initial, d'où `benefice => 10000` au cycle 0.
Ce résultat ne mesure pas le bonus, qui s'évalue à **50 000 cycles**.
Dans l'implémentation actuelle, `time` en premier critère (comme pour `steak`
et `ikea`) impose un horizon interne de 500 cycles, indépendamment de l'argument.

## 📋 Tableau des commandes make

| Commande | Description |
| --- | --- |
| `make` | Synchronise le projet dans `.venv`, sans écrire dans le dossier personnel |
| `make install` | Synchronise `.venv` depuis `uv.lock` avec uv |
| `make install-bin` | Crée les symlinks `krpsim` / `krpsim_verif` dans `~/.local/bin` |
| `make shell` | Ouvre un shell interactif dans le virtualenv |
| `make krpsim <resource_file> <max_cycles>` | Lance la simulation |
| `make krpsim_verif <resource_file> <trace_file>` | Vérifie une trace |
| `make test` | Exécute les tests |
| `make lint` | Exécute le lint et le typage |
| `make format` | Formate le code (`black`, `isort`) |
| `make process_resources` | Batch sur tous les fichiers de `resources` |
| `make clean` | Nettoie les artefacts temporaires |
| `make fclean` | Nettoyage complet, y compris `.venv` |
| `make doctor` | Vérifie uv, Python, `uv.lock` et l'état de l'environnement |
| `make help` | Affiche l’aide des cibles |

<a id="formats-entree"></a>

## 📝 Formats d'entrée

Les fichiers de configuration décrivent les stocks initiaux puis les processus sous forme `name:(need):(result):delay`.
La durée `delay` d'un processus doit être positive ou nulle. Une durée `:0`
décrit un processus instantané : ses besoins sont consommés et ses résultats
sont crédités au même cycle.

### Ordonnancement et optimisation

L'ordonnanceur construit le graphe inverse des ressources à partir des cibles
`optimize`. Il compare les producteurs selon le gain lexicographique attendu,
la consommation de ressources et la durée, puis développe leurs dépendances en
lots. Les stocks intermédiaires, sous-produits et ressources réutilisables sont
pris en compte sans dépendre des noms présents dans la configuration.

Avec `time` en premier critère, une anticipation bornée compare aussi les lots
suivants : elle privilégie la production atteignable, puis sa durée cumulée.
Les besoins sont revérifiés ensemble après la préparation des dépendances pour
éviter de compter deux fois une même ressource. Cette heuristique ne garantit
pas l'optimum global sur tous les graphes. Sur `steak`, elle cuit les trois
steaks en 30 cycles (`cuisson_1`, `cuisson_3`, `cuisson_2`).

Si aucun plan complet n'est trouvé, le diagnostic distingue l'épuisement du
budget d'exploration d'un échec de l'heuristique. Le simulateur peut alors
produire des ressources intermédiaires liées à l'objectif, avec les stocks
réellement disponibles et sans dépasser l'horizon. Ce repli conserve les
objectifs déjà acquis et les ressources réutilisables (comme `clock`) ; il
préfère les conversions disponibles aux sources renouvelables, évite de
revisiter un état et respecte un budget de trace. Il ne garantit pas l'optimum
et ne relance pas la recherche complète à chaque cycle.

Avec `resources/time` et `optimize:(year)`, une limite de 50 cycles produit
50 `second`, conserve `clock:1` et laisse `year:0`. Avec `optimize:(time;year)`,
l'horizon interne reste de 500 cycles : le repli produit 7 `minute` et 38
`second`, avec `clock:1` et `year:0`. Les traces sont vérifiables et la sortie
signale explicitement la production intermédiaire. Une recherche infructueuse
n'est plus présentée comme une preuve qu'aucune amélioration n'est possible.

Un même processus peut être lancé plusieurs fois au même cycle. Les processus
instantanés sont exécutés jusqu'à la multiplicité utile, avec une protection
contre les boucles instantanées sans progression. Lorsqu'un convertisseur final
instantané est détecté, sa ressource d'entrée reste disponible comme fonds de
roulement pendant la production et n'est convertie qu'à la fin.

Une production directe à délai positif qui consomme sa propre ressource cible
peut lancer plusieurs instances, financées uniquement par les stocks disponibles
au début du lot. Avec `resources/self`, les lancements doublent : 1 au cycle 0,
2 au cycle 1, 4 au cycle 2, soit 8 unités de `X` au cycle 3.
Pour ces lots, un budget de 100 000 lignes, trace déjà produite comprise, borne
la recherche. Le dernier lot utilise le budget restant puis se termine ; les
stocks finaux et la trace classique sont enregistrés normalement. Un message
signale la recherche bornée, sans garantie d'optimalité, avec un code retour 0.
Les éventuelles conversions terminales restent exécutées après ce lot.
Ainsi, `resources/self 50` produit 100 000 lancements vérifiables et 100 001
unités de `X` au cycle 17. Cette solution est réalisable dans les 50 cycles
demandés ; elle ne représente pas l'optimum théorique de 2⁵⁰ unités.

Le vérificateur rejoue directement la trace fournie : il accepte donc tout
ordonnancement valide, y compris les répétitions au même cycle et les solutions
différentes de celle choisie par `krpsim`.

Exemple (`resources/ikea`):

```txt
#
# ikea demo - krpsim
#
# stock      name:quantity
planche:7
#
# process   name:(need1:qty1;need2:qty2;[...]):(result1:qty1;result2:qty2;[...]):delay
#
do_montant:(planche:1):(montant:1):15
do_fond:(planche:2):(fond:1):20
do_etagere:(planche:1):(etagere:1):10
do_armoire_ikea:(montant:2;fond:1;etagere:3):(armoire:1):30
#
# optimize time for 0 stock and no process possible,
# or maximize some products over a long delay
# optimize:(stock1;stock2;...)
#
optimize:(time;armoire)
#
```

## 🖥️ Exemple de sortie: simulation

```bash
make krpsim resources/ikea 10
[KRPSIM] Exécution: file=resources/ikea, max_cycles=10
[KRPSIM] Trace de sortie: trace_ikea.txt
Nice file! 4 processes, 5 stocks, 1 to optimize
Evaluating ... done.
Main walk:
Optimization criteria: time, armoire
0:do_etagere
0:do_montant
0:do_fond
1:do_etagere
1:do_montant
2:do_etagere
20:do_armoire_ikea
No more process doable at time 51
Final Stocks:
  armoire  => 1
  etagere  => 0
  fond     => 0
  montant  => 0
  planche  => 0
```

## ✅ Exemple de sortie: vérification

```bash
make krpsim_verif resources/ikea trace_ikea.txt
[KRPSIM_VERIF] Vérification: file=resources/ikea, trace=trace_ikea.txt
trace is valid
Final Stocks:
  armoire  => 1
  etagere  => 0
  fond     => 0
  montant  => 0
  planche  => 0
Last cycle: 51
```

## 🗂️ Structure du projet

Commande utilisée:

```bash
tree -L 2
```

Sortie:

```txt
.
├── .python-version
├── author
├── codecov.yml
├── docs
│   ├── AGENTS.md
│   ├── krpsim.en.subject.pdf
│   ├── Lois de Murphy.KRPSIM.txt
│   ├── optimize_marelle-bonbon.png
│   ├── optimize_marelle.png
│   ├── optimize_stock1.png
│   ├── optimize_stock1-stock2.png
│   ├── optimize_stock2-stock1.png
│   ├── optimize_time-marelle.png
│   ├── pipeline.md
│   └── WBS_krpsim.txt
├── LICENSE
├── Makefile
├── pyproject.toml
├── README.md
├── resources
│   ├── bad_proc
│   ├── bad_ref
│   ├── bad_stock
│   ├── best
│   ├── big
│   ├── delay0
│   ├── dup
│   ├── expo
│   ├── finite
│   ├── greedy
│   ├── ikea
│   ├── init0
│   ├── lexi
│   ├── loop
│   ├── multi_out
│   ├── no_goal
│   ├── obj2
│   ├── pomme
│   ├── recre
│   ├── self
│   ├── simple
│   ├── steak
│   └── time
├── src
│   ├── krpsim
│   └── krpsim_verif
├── tests
│   ├── __init__.py
│   ├── test_cli.py
│   ├── test_display.py
│   ├── test_parser_hypothesis.py
│   ├── test_parser.py
│   ├── test_simulator.py
│   ├── test_verifier.py
│   └── test_version.py
├── trace_ikea.txt
├── trace_simple.txt
└── uv.lock

```

<a id="tests"></a>

## 🧪 Tests

```bash
make test
```

Les scénarios de la grille sont automatisés dans `tests/test_evaluation.py`.
Le [compte rendu de validation](docs/evaluation.md) détaille les résultats,
les commandes reproductibles et les limites de cette vérification.

<a id="qualite-du-code"></a>

## 🔍 Qualité du code

* **Formatage** : `black` et `isort`.
* **Lint** : `ruff`.
* **Typage** : `mypy`.
* **Hooks** : `pre-commit`.

## 📚 Documentation

- [Pipeline global](docs/pipeline.md)
- [Répartition de l'apprentissage — Sylvanna et Rafael](docs/repartition-apprentissage.md)
- [Sujet du projet 42 (PDF)](docs/krpsim.en.subject.pdf)

## 👥 Auteurs

- **Rafael VERISSIMO** — [Portfolio](https://raveriss.dev/) · [LinkedIn](https://www.linkedin.com/in/verissimo-rafael/) · [GitHub](https://github.com/raveriss)
- **Paul BEAUDET** — [LinkedIn](https://www.linkedin.com/in/paul-beaudet-968860385/) · [GitHub](https://github.com/PaulBeaudet23)
- **Sylvanna COURBIS** — [GitHub](https://github.com/Sycourbi)
  
## 🛡️ Licence

Projet distribué sous licence MIT.
