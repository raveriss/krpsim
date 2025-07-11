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

---

## 🤝 Phase 5 — Politique de Contribution et Pull Requests (PR)

Pour garantir que chaque ajout au projet respecte la charte de qualité et l'architecture définie, toute modification du code doit obligatoirement passer par une Pull Request. Ce processus assure la revue par les pairs, la validation automatisée et la traçabilité.

### Principes Directeurs
-   **PRs de petite taille** : Chaque PR doit être aussi petite que possible et se concentrer sur une seule tâche atomique du WBS (Phase 4). Une PR plus petite est plus rapide à réviser et moins risquée à intégrer.
-   **Le créateur est le premier validateur** : Ne soumettez une PR que si vous êtes convaincu qu'elle respecte tous les critères de qualité. Exécutez l'ensemble des tests en local avant de demander une revue.
-   **La CI est reine** : Une PR ne peut être fusionnée que si la CI (GitHub Actions) est au vert. Aucune exception.

### Cycle de Vie d'une Pull Request

Chaque contributeur doit suivre ces étapes :

#### 1. ✅ Avant la Création (en local)
Avant de pousser votre branche et de créer une PR, vous **devez** lancer les commandes suivantes pour vous assurer que tout est conforme :
```bash
make format  # Formate le code avec black et isort
make lint    # Vérifie la qualité du code avec ruff
make test    # Lance les tests et vérifie la couverture de 100%
```
Assurez-vous également que votre branche est à jour avec la branche principale (main ou develop) pour éviter les conflits.

### 2. 📝 Création de la Pull Request
-   **Titre clair et concis** : Utilisez des préfixes comme feat:, fix:, refactor:, test:.

Exemple : feat(parser): Ajout de la validation des stocks initiaux
-   **Description détaillée :**
        - **Quoi ?** Un résumé des changements.
        - **Pourquoi ?** La raison de ces changements (ex: "Implémente la tâche X du WBS").
        - **Comment ?** Une brève explication de l'approche technique si nécessaire.
        - **Lien vers le WBS** : Mentionnez l'ID de la tâche de la Phase 4 que cette PR résout.

### 3. 🤖 Validation Automatisée (CI)
Dès sa création, la PR déclenche le workflow défini dans `.github/workflows/ci.yml`. Ce dernier exécute automatiquement les mêmes vérifications que celles que vous avez faites en local (`lint`, `mypy`, `pytest --cov`).

### 4. 🧑‍💻 Revue par les Pairs (Peer Review)
    - Au moins une **approbation** d'un autre membre de l'équipe est requise.
    - Le réviseur doit vérifier :
        - 1. Le **respect de la** `Charte de Qualité des Tests` (Phase 2).
        - 2. La **logique métier** et la pertinence de l'implémentation.
        - 3. La **clarté** et la **lisibilité** du code.
        - 4. L'absence de code commenté ou de `print()` de débogage.

### 5. 🚀 Fusion (Merge)
-    **Conditions** : La CI doit être au vert (✅) ET la PR doit avoir reçu au moins une approbation.
-    **Méthode** : Privilégier le `Squash and merge` pour conserver un historique `git` propre sur la branche principale. Le message de commit doit être soigné et résumer l'apport de la PR.
-    Nettoyage : La branche de la PR doit être supprimée après la fusion.