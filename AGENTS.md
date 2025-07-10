# AGENTS.md — Plan de Développement TDD, Architecture et WBS pour krpsim

Ce document définit les fondations techniques, l’architecture logicielle, la stratégie TDD et le plan d’exécution détaillé (WBS) pour le projet **krpsim**, tout en intégrant la mitigation des risques.

---

## 🔧 Phase 0 — Fondations Techniques & Outillage

Cette phase pose l’environnement de développement professionnel et automatisé.

### Gestion de version (`git`)
- [ ] Initialiser le dépôt **Git**
- [ ] Créer un `README.md` détaillé (description, usage, badges CI/CD)
- [ ] Ajouter un fichier `LICENSE` (ex: MIT)
- [ ] Créer le fichier `author` si requis

### Environnement & Dépendances (`poetry`)
- [ ] Initialiser le projet avec `poetry init`
- [ ] Ajouter les dépendances de dev : `pytest`, `pytest-cov`, `black`, `ruff`, `isort`, `mypy`

### Qualité, Formatage, Linting
- [ ] Configurer `black`, `isort`, `ruff` et `mypy` dans `pyproject.toml`
- [ ] Créer un `Makefile` avec des commandes standard : `install`, `test`, `lint`, `format`, `run`

### Tests & Assurance Qualité
- [ ] Configurer `pytest` et `pytest-cov` pour exiger 100% de couverture de code (`--cov-fail-under=100`)

### CI/CD (GitHub Actions)
- [ ] Mettre en place un workflow `.github/workflows/ci.yml` qui exécute lint, mypy et pytest --cov à chaque `push` et `pull_request`

---

## 📂 Phase 1 — Architecture des Agents

Définition de la structure logique cible du projet.

### Arborescence
```bash
krpsim/
├── krpsim.py
├── krpsim_verif.py
├── resources/
│   ├── ikea
│   ├── inception
│   ├── pomme
│   ├── recre
│   ├── simple
│   ├── steak
│   └── (vos_fichiers_personnels.txt)
├── src/
│   ├── init.py
│   ├── parser.py
│   ├── simulator.py
│   ├── optimizer.py
│   └── display.py
└── tests/
    ├── init.py
    ├── test_parser.py
    ├── test_simulator.py
    └── test_verifier.py
```
### Rôle des Agents
- 🤖 **Agent 1 — L’Analyseur (`src/parser.py`)** : lit et valide le fichier de config
- ⚙️ **Agent 2 — Le Simulateur (`src/simulator.py`)** : gère l’état et l’exécution
- 🧠 **Agent 3 — L’Optimiseur (`src/optimizer.py`)** : décide quels processus lancer à chaque cycle
- ✅ **Agent 4 — Le Vérificateur (`krpsim_verif.py`)** : valide une trace de sortie
- 🧪 **Agent 5 — Assurance Qualité (`tests/`)** : garantit la fiabilité via des tests (100% couverture)
- 🎨 **Agent 6 — Présentateur (`src/display.py`)** : gère l’affichage utilisateur (distinct de la trace machine)

---

## 🎯 Phase 2 — Charte de Qualité des Tests (Définition du Fait, 100% utile)

Une fonctionnalité n’est considérée “Done” que si l’ensemble des tests associés respecte ces règles.

### 🧪 Couverture Fonctionnelle
- [ ] Chaque fonction a un test unitaire dédié
- [ ] Chaque fonction testée avec :
  - [ ] Au moins 1 entrée valide
  - [ ] Au moins 1 entrée invalide
  - [ ] Tous les cas limites (vide, extrême, None, etc.)
- [ ] Tous les chemins if/else couverts
- [ ] Toutes les boucles testées (0, 1, N itérations)

### 💥 Gestion des Erreurs & Exceptions
- [ ] Chaque bloc try/except est couvert (cas nominal ET exception)
- [ ] Tous les messages d’erreur personnalisés sont testés
- [ ] Les assertions d’erreur (`pytest.raises`) sont systématiques

### 🧠 Logique Métier
- [ ] Chaque règle métier des specs est testée
- [ ] Chaque contrainte métier vérifiée (formats, limites)

### 🧪 Taux de Couverture
- [ ] Objectif : 100% (`--cov-fail-under=100`)

### 🧼 Nettoyage des Tests
- [ ] Aucun `# pragma: no cover` injustifié
- [ ] Aucun test sans assert

---

## 📚 Phase 3 — Corpus de Test de Référence

Tous les agents s’appuient sur le corpus de fichiers de configuration de `resources/`, en respectant la charte de qualité.

- `simple` : scénario linéaire de base
- `ikea` : graphe de dépendances simple
- `steak` : chemins multiples pour un même objectif
- `pomme` : graphe complexe
- `recre` : processus variés (conso/gain/perte)
- `inception` : système auto-soutenable (test de boucles)

---

## 📋 Phase 4 — Plan d’Exécution (WBS) en TDD

Chaque tâche est liée à un risque identifié et validée contre le corpus de test.

### **Module 1 : L’Analyseur (Agent 1)**
- [ ] **Test (Rouge)** : tests unitaires sur chaque fichier du corpus (cas valides)
- [ ] **Implémentation (Vert)** : parsing & validation
- [ ] **Test (Rouge)** : tests sur cas invalides, limites (fichier vide, erreur lecture) *(Mitige: Risk-1, Risk-3)*
- [ ] **Implémentation (Vert)** : renforcer validation & gestion erreurs
- [ ] **Refactoring** : amélioration structure code parsing

### **Module 2 : Le Simulateur (Agent 2)**
- [ ] **Test (Rouge)** : tests sur `steak`/`inception` (simultanéité, boucles) *(Mitige: Risk-2)*
- [ ] **Implémentation (Vert)** : logique du simulateur

### **Module 3 : Intégration & Application Principale**
- [ ] **Test (Rouge)** : tests d’intégration (trace vs résultat attendu) *(Mitige: Risk-7)*
- [ ] **Implémentation (Vert)** : orchestration agents dans `krpsim.py`

### **Module 4 : Le Vérificateur (Agent 4)**
- [ ] **Test (Rouge)** : vérification sur trace valide/invalide (`ikea`) *(Mitige: Risk-8)*
- [ ] **Implémentation (Vert)** : logique finale du vérificateur

### **Module 5 : Finalisation**
- [ ] **Optimiseur** : implémenter/tester stratégies (Agent 3, objectifs variés du corpus) *(Mitige: Risk-5)*
- [ ] **Documentation** : mise à jour du `README.md`
- [ ] **Revue finale** : s’assurer que tous les tests passent & charte qualité respectée


