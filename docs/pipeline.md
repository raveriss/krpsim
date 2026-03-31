# Pipeline global KRPSIM

Ce document décrit le flux d'exécution complet de KRPSIM, de la lecture d'un fichier de configuration jusqu'à la génération d'un graphe Gantt.

## Vue d'ensemble

```mermaid
flowchart LR
    A[Fichier de configuration] --> B[Parser]
    B --> C[Optimizer]
    C --> D[Simulator]
    D --> E[Trace machine]
    E --> F[Verifier]
    F --> G[Graph Config JSON]
    G --> H[Diagramme de Gantt PNG]
```

## 1. Entrée: configuration

Le fichier d'entrée (ex: `resources/ikea`) contient:

- Les stocks initiaux.
- La définition des processus.
- Optionnellement une stratégie d'optimisation (`optimize:(...)`).

Format processus:

```txt
process_name:(needs):(results):delay
```

## 2. Parsing et validation

Module: `src/krpsim/parser.py`

Le parser:

- Vérifie la grammaire.
- Détecte les doublons et les quantités invalides.
- Construit une `Config` fortement typée (`stocks`, `processes`, `optimize`).

En cas d'erreur, une `ParseError` est levée.

## 3. Ordonnancement

Module: `src/krpsim/optimizer.py`

La fonction `order_processes` trie les processus de manière déterministe:

- Selon les critères de `optimize` (ex: `time`, puis stock cible).
- Avec un tie-break stable par nom de processus.

## 4. Simulation cycle-par-cycle

Module: `src/krpsim/simulator.py`

Le moteur:

- Consomme les ressources d'entrée (`needs`) au démarrage des processus.
- Produit les ressources de sortie (`results`) à la fin du `delay`.
- Avance le temps uniquement quand une activité est en cours.
- Génère une trace ordonnée `(cycle, process_name)`.

Sorties principales:

- Trace texte: `trace_<resource>.txt`
- État final des stocks.

## 5. Vérification de trace

Modules: `src/krpsim_verif/verifier.py`, `src/krpsim_verif/cli.py`

Le vérificateur:

- Parse la trace fournie (`cycle:process`).
- Rejoue la simulation attendue.
- Compare trace fournie vs trace attendue.
- Retourne l'état final si la trace est valide.

## 6. Génération des artefacts de graphe

Modules: `gantt_project/build_graph_config.py`, `gantt_project/gantt.py`

Après `make krpsim` ou `make krpsim_verif`, le pipeline produit:

- `graph_config_<resource>.json` (intermédiaire)
- Un graphe Gantt (PNG) via `gantt.py`

Exemple d'image: [diagramme_gantt_ikea.png](diagramme_gantt_ikea.png)

## Commandes de bout en bout

```bash
make krpsim resources/ikea 10
make krpsim_verif resources/ikea trace_ikea.txt
```

## Références

- [README principal](../README.md)
- [Sujet KRPSIM 42](krpsim.en.subject.pdf)
