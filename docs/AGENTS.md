
# AGENTS.md — Blueprint de Développement, Qualité, Checklist et Loi de Murphy (KRPSIM)

Ce document est à la fois :
- **Le plan d’action structuré** pour concevoir, coder et valider chaque module du projet.
- **Une checklist exhaustive** pour résister à la Loi de Murphy, automatiser les tests, la CI/CD, et industrialiser la maintenance.
- **Un guide pédagogique** traçable et exploitable par n’importe quelle IA ou dev humain.

---

## 0. 🏗️ Fondations Techniques & Outillage

### 0.1 Gestion de version (`git`)
- [ ] Initialiser dépôt **Git** et créer le `README.md` (description, usage, badges CI/CD)
- [ ] Ajouter `LICENSE` (MIT) et fichier `author`

### 0.2 Environnement & Dépendances (`uv`)
- [ ] Initialiser le projet avec uv et déclarer les dépendances dev dans `dependency-groups` : `pytest`, `pytest-cov`, `black`, `ruff`, `isort`, `mypy`

### 0.3 Qualité, Formatage, Linting
- [ ] Configurer : `black`, `isort`, `ruff`, `mypy` dans `pyproject.toml`
- [ ] Créer `Makefile` : `install`, `test`, `lint`, `format`, `run`

### 0.4 CI/CD (GitHub Actions)
- [ ] `.github/workflows/ci.yml` avec : lint, mypy, pytest --cov à chaque `push`/`pull_request`
- [ ] Couverture de code 100% obligatoire (`--cov-fail-under=100`)

---

## 1. 📂 Architecture des Agents (Blueprint)

> **Le projet est découpé en agents spécialisés, pour une séparation stricte des responsabilités.**

### Arborescence cible
```

krpsim/
├── krpsim.py
├── krpsim\_verif.py
├── resources/
│   ├── simple, ikea, steak, pomme, recre, time, (fichiers extrêmes/crash)
├── src/
│   ├── **init**.py
│   ├── parser.py        # Agent 1 : Analyseur
│   ├── simulator.py     # Agent 2 : Simulateur
│   ├── optimizer.py     # Agent 3 : Optimiseur
│   └── display.py       # Agent 6 : Présentateur
└── tests/
├── **init**.py
├── test\_parser.py
├── test\_simulator.py
└── test\_verifier.py  # Agent 5 : QA

```

#### **Rôles**
- 🤖 **Agent 1 (parser.py)** : lecture, parsing, validation stricte du fichier de config.
- ⚙️ **Agent 2 (simulator.py)** : gestion des cycles, états, logique de simulation.
- 🧠 **Agent 3 (optimizer.py)** : décision/exécution optimisée, respect du paramètre `optimize:`.
- ✅ **Agent 4 (krpsim_verif.py)** : vérification de la conformité des traces.
- 🧪 **Agent 5 (tests/)** : couverture des cas extrêmes, robustesse (TDD, fuzzing).
- 🎨 **Agent 6 (display.py)** : affichage utilisateur, sortie machine.

---

## 2. 🧪 Charte de Qualité et Plan de Tests

> **Tout module/fonction est validé par TDD, 100% de couverture, cas extrêmes, et fuzzing.**

- [ ] **Couverture fonctionnelle** : entrées valides, invalides, limites, edge-cases.
- [ ] **Couverture logique** : tous chemins (if/else, boucles 0/1/N itérations).
- [ ] **Gestion des erreurs** : `try/except`, messages d’erreur, crash test.
- [ ] **Taux de couverture** : 100% strict (`--cov-fail-under=100`).
- [ ] **Fuzzing** : injection unicode, binaire, logs longs, permissions.
- [ ] **Tests crash/disque plein/SIGINT**.

---

## 3. 📚 Corpus de Test de Référence

- [ ] Utilisation de tous les fichiers : `simple`, `ikea`, `steak`, `pomme`, `recre`, `time`, **et fichiers de stress/crash**.
- [ ] Générer 2 fichiers custom : un qui termine, un “boucle infinie”.

---

## 4. 📋 WBS Structuré & Checklists (Plan d’Action + Checklist)

### **Epic 1 : Parsing & Validation (Agent 1)**
  - [ ] Vérifier existence, droits, type texte, UTF8, CRLF, BOM, chars spéciaux
  - [ ] Valider sections, extension, dédoublonnage, overflow lignes >255 chars
  - [ ] Parsing : ignorer commentaires/vides [cite: 110], parser stocks [cite: 111], process [cite: 113], optimize [cite: 115]
  - [ ] Validation stricte : unicité, quantités positives, dépendances, erreurs format (parenthèses, séparateurs)

### **Epic 2 : Simulation & Optimisation (Agents 2 & 3)**
  - [ ] Implémenter un modèle à temps discret (cycles)
  - [ ] Gérer l’état des stocks à chaque cycle (consommation/production)
  - [ ] Détecter processus exécutables, exécution simultanée [cite: 114]
  - [ ] Logique d’optimisation : stratégie de base et avancée [cite: 102]
  - [ ] Conditions d’arrêt : fin de simulation, détection boucle infinie (watchdog, deadlock, starvation) [cite: 128, 129]
  - [ ] Gestion du paramètre `<delay>` : validation, timeout strict, message si excès

### **Epic 3 : Affichage, Traces, Vérification (Agents 4 & 6)**
  - [ ] Affichage clair des actions et de l’état final [cite: 126]
  - [ ] Générer sortie machine `<cycle>:<process_name>` [cite: 127]
  - [ ] Vérifier la trace (cohérence, format, logs flush, crash, disque plein) [cite: 134, 135, 136, 137]

### **Epic 4 : Sécurité, Robustesse & Maintenance**
  - [ ] Gestion des erreurs : messages clairs, codes sortie ≠0, crash tests
  - [ ] Protection path traversal, injection shell, unicode dangereux
  - [ ] Fuzzing sur entrées, logs, permissions, fichiers binaires
  - [ ] Instrumentation mémoire (profiling, valgrind, memory leak)
  - [ ] Cross-platform : Linux/Mac/Windows, Python ≥3.10
  - [ ] Gestion SIGINT/SIGTERM, rollback
  - [ ] Documentation à jour : README, docstrings, guide utilisateur, changelog, roadmap, guide contributeur

---

## 5. 🛡️ Table des Risques (Loi de Murphy) — Mapping actionnable

| ID  | Domaine       | Description synthétique                                     | Mitigation prévue                         |
|-----|--------------|-------------------------------------------------------------|-------------------------------------------|
| R01 | Fichier/IO   | Fichier absent, corrompu, droits insuffisants               | Try/Except, message clair, exit 1         |
| R02 | Parsing      | Encodage, format, champs manquants, lignes trop longues     | Validation stricte, tests, logs, exit     |
| R03 | Simulation   | Boucle infinie, deadlock, starvation, overflow              | Watchdog, détection, tests limites        |
| R04 | Mémoire      | Explosion RAM, fuite, corruption, double-free               | Profiling, valgrind, gestion stricte      |
| R05 | Vérif/Tests  | Trace incohérente ou inexploitable, logs non flushés        | Tests auto, checker, flush                |
| R06 | Sécurité     | Path traversal, injection shell, crash volontaire           | Sanity check, sandboxing, fuzzing         |
| R07 | Performance  | Débordement temps, CPU/RAM, non-respect `<delay>`           | Timeout, monitoring, logs                 |
| R08 | UX/CLI       | Mauvais args, absence d’aide, version non traçable          | Help complet, --version, validation       |
| R09 | Logging      | Logs inexploitables, logs trop longs, disque plein           | Flush, tests crash, checker logs          |
| R10 | Maintenance  | Docs absentes, code non commenté, pas de roadmap            | docstring, README, roadmap, guide contrib |
| ... | ...          | (cf. fichier “Lois de Murphy” pour liste exhaustive)        | ...                                       |

> **Chaque tâche, chaque test, chaque mitigation dans le WBS est mappée à cette table.**

---

## 6. 🤝 Politique de Contribution et Pull Requests (PR) — Processus qualité

- PRs atomiques, petites, reliées à une tâche/sous-tâche du WBS (liens [cite: 114] si pertinent)
- CI/CD obligatoire au vert (lint, test, couverture 100%)
- Description PR : quoi/pourquoi/comment, ID WBS, liens exigences sujet
- **Cycle de vie PR** :
    - [ ] Tests locaux (format, lint, test, coverage)
    - [ ] Exécuter toute la suite de tests avant chaque commit ;
          si la modification d'un test implique un changement
          d'implémentation, lancer ces tests en premier puis
          relancer l'ensemble dans l'ordre logique
    - [ ] Branche à jour/main
    - [ ] Titre normé (`feat:`, `fix:`, `refactor:`, `test:`…)
    - [ ] Revue pair, squash & merge, suppression branche
- Toute fusion = ajout au changelog et checklist de maintenance à jour.

---

## 7. ⏱️ Gestion stricte du paramètre `<delay>`

- **Validation CLI** : usage, 2 arguments obligatoires
- **Vérification numérique** : delay = int positif
- **Timeout global** : simulation doit respecter le délai
- **Test automatique** : fichier forçant un dépassement de délai
- **Message d’erreur** : clair, exit code ≠0

---

## 8. 📖 Maintenance, Documentation et Roadmap

- Docstring systématiques, README à jour (structure, usage, FAQ, exemples)
- Changelog, guide contributeur, plan de maintenance/monitoring
- Roadmap pour évolutions futures (ex: support multi-thread, nouvelles stratégies)

---

## 9. 🧠 Synthèse — Pourquoi cette structure ?

- **Hiérarchisation claire** : chaque agent, chaque Epic, chaque sous-tâche
- **Mapping Loi de Murphy** : tout problème identifié = une case checklistée/testée
- **Traçabilité** : chaque exigence du sujet est citée, chaque mitigation explicitée
- **Scalabilité et automatisation** : idéal pour Codex, CI/CD, et future maintenance
- **Explicatif et actionnable** : aussi lisible par un humain qu’exploitable par une IA
