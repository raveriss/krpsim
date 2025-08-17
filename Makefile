# Makefile pour automatiser l'installation, le linting,
# le formatage, les tests et l'exécution de krpsim

# Déclaration des cibles sans fichier associé
.PHONY: install dev-install lint format test krpsim krpsim_verif process_resources clean fclean re uninstall

# Variable pour préfixer les commandes Poetry
POETRY = poetry run

# ------------------------------------------------------------
# Installation des dépendances
# ------------------------------------------------------------
install:
	# Installe les bibliothèques listées dans pyproject.toml
	poetry install
	poetry run python -m pip install -e .

# ------------------------------------------------------------
# Qualité de code : lint et typage statique
# ------------------------------------------------------------
lint:
	# Vérifie le style et l'erreurs via ruff
	$(POETRY) ruff check src tests	
	# Vérifie les annotations de types avec mypy
	$(POETRY) mypy src tests

# ------------------------------------------------------------
# Mise en forme automatique du code
# ------------------------------------------------------------
PY_FILES := $(shell git ls-files '*.py')

format:
	@if [ -n "$(PY_FILES)" ]; then \
		$(POETRY) black $(PY_FILES); \
		$(POETRY) isort $(PY_FILES); \
	else \
		echo "Aucun fichier Python détecté via git ls-files."; \
	fi

# ------------------------------------------------------------
# Exécution de la suite de tests
# ------------------------------------------------------------
test:
	# Lance pytest pour vérifier le bon fonctionnement des modules
	$(POETRY) pytest

# ------------------------------------------------------------
# Cibles pour exécuter krpsim et sa vérification
# ------------------------------------------------------------
krpsim:
	# Exécute krpsim avec les arguments passés après "make krpsim"
	$(POETRY) krpsim $(filter-out $@,$(MAKECMDGOALS))

krpsim_verif:
	# Exécute krpsim_verif avec les arguments passés après "make krpsim_verif"
	$(POETRY) krpsim_verif $(filter-out $@,$(MAKECMDGOALS))

# ------------------------------------------------------------
# Traitement en batch de toutes les ressources
# ------------------------------------------------------------
process-resources:  # alias pratique pour O/I
	@echo "=== Début du traitement de toutes les ressources ==="
	@for f in resources/*; do \
	  # Pour chaque fichier de ressources
	  echo "=== Traitement de $$f ==="; \
	  $(POETRY) krpsim "$$f" 10; \
	  echo "=== Vérification de $$f ==="; \
	  $(POETRY) krpsim_verif "$$f" trace.txt; \
	  sleep 3; \
	done > log.txt
	@echo "=== Traitement terminé : voir log.txt pour le détail ==="

# -------------------------------------------------------------------
# Uninstall / Clean / Fclean / Re
# -------------------------------------------------------------------

# Désinstalle le paquet du venv courant si présent (sans casser le pyproject)
uninstall:
	-$(POETRY) python -m pip uninstall -y krpsim || true

# Supprime artefacts de build/tests/logs
clean:
	@echo "Nettoyage des artefacts…"
	@rm -rf \
	  build/ dist/ \
	  .pytest_cache/ .mypy_cache/ \
	  .coverage coverage.xml htmlcov/ \
	  .ruff_cache/ .tox/ \
	  **/__pycache__/ \
	  log.txt trace.txt junit.xml \
	  .artifacts/ docs/graphs/*.png

# clean + désinstalle + supprime le venv Poetry (optionnel mais radical)
fclean: clean
	@echo "Désinstallation du package dans le venv Poetry…"
	-$(POETRY) python -m pip uninstall -y krpsim || true
	@echo "Suppression du venv Poetry…"
	-poetry env remove python || true

# Re = fclean + install
re: fclean install

# ------------------------------------------------------------
# Gestion des targets inconnues sans erreur ni timestamps
# ------------------------------------------------------------
.DEFAULT:
	@:
