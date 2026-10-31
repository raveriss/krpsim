# Makefile pour automatiser l'installation, le linting,
# le formatage, les tests et l'exécution de krpsim
#
# Usage express :
#   make                -> installe le projet dans .venv
#   make krpsim ...     -> exécute krpsim depuis .venv

.PHONY: default install install-bin uninstall-bin \
        lint format test krpsim krpsim_verif process_resources \
        clean fclean re uninstall which-bin print-path help doctor \
			ensure-uv shell venv-shell

MAKEFLAGS += --no-print-directory
UV_BIN ?= $(shell command -v uv 2>/dev/null || printf '%s' "$(HOME)/.local/bin/uv")
UV_LINK_MODE ?= copy
VENV_DIR = .venv
VENV_PYTHON = $(VENV_DIR)/bin/python
PROJECT_VENV = $(abspath $(VENV_DIR))
UV_RUN = UV_PROJECT_ENVIRONMENT="$(PROJECT_VENV)" $(UV_BIN) run --no-sync
PINNED_PYTHON_VERSION := $(strip $(shell sed -n '1p' .python-version 2>/dev/null || printf '3.13'))
KRPSIM_INPUT = $(word 2,$(MAKECMDGOALS))
KRPSIM_CYCLES = $(word 3,$(MAKECMDGOALS))
KRPSIM_VERIF_INPUT = $(word 2,$(MAKECMDGOALS))
KRPSIM_VERIF_TRACE = $(word 3,$(MAKECMDGOALS))
KRPSIM_ARGS_COUNT = $(words $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS)))
CLI_ARG_TARGETS = krpsim krpsim_verif
INSTALL_GOAL_REQUESTED = $(filter install,$(MAKECMDGOALS))

ifneq (,$(filter $(firstword $(MAKECMDGOALS)),$(CLI_ARG_TARGETS)))
CLI_ARGS = $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
.PHONY: $(CLI_ARGS)
$(foreach arg,$(CLI_ARGS),$(eval $(arg):;@:))
endif

# ------------------------------------------------------------
# [DEFAULT] Installation locale au projet
# ------------------------------------------------------------
default: install
	@echo "✅ Installation terminée."
	@echo "   Ex.: make krpsim resources/ikea 10"

# ------------------------------------------------------------
# INSTALL : uv choisit/télécharge Python, crée .venv et synchronise uv.lock.
# Les appels suivants sont incrémentaux grâce au cache natif de uv.
# ------------------------------------------------------------
ensure-uv:
	@set -eu; \
	if [ ! -x "$(UV_BIN)" ]; then \
		echo "❌ uv est requis mais introuvable: $(UV_BIN)"; \
		echo "   Installation: curl -LsSf https://astral.sh/uv/install.sh | sh"; \
		echo "   Puis relance: make"; \
		exit 1; \
	fi

install: ensure-uv
	@echo "# Synchronisation de l'environnement avec uv"
	@set -eu; \
	if ! $(UV_BIN) python find --no-python-downloads "$(PINNED_PYTHON_VERSION)" >/dev/null 2>&1; then \
		echo "# Installation de Python $(PINNED_PYTHON_VERSION) avec uv"; \
		$(UV_BIN) python install "$(PINNED_PYTHON_VERSION)"; \
	fi
	@set -eu; \
	if [ -e "$(VENV_DIR)" ] && [ ! -d "$(VENV_DIR)" ]; then \
		echo "❌ $(VENV_DIR) existe mais n'est pas un répertoire."; \
		echo "   Action: déplace ou supprime ce fichier, puis relance make."; \
		exit 1; \
	fi; \
	if [ -L "$(VENV_DIR)" ] && [ ! -x "$(VENV_PYTHON)" ]; then \
		echo "❌ $(VENV_DIR) est un lien symbolique vers un environnement invalide."; \
		echo "   Action: corrige ou supprime ce lien, puis relance make."; \
		exit 1; \
	fi; \
	if [ -d "$(VENV_DIR)" ] && [ ! -x "$(VENV_PYTHON)" ]; then \
		echo "# Réparation de l'environnement Python incomplet: $(VENV_DIR)"; \
		$(UV_BIN) venv --clear --force --python "$(PINNED_PYTHON_VERSION)" "$(VENV_DIR)"; \
	fi
	@UV_PROJECT_ENVIRONMENT="$(PROJECT_VENV)" $(UV_BIN) sync --locked --python "$(PINNED_PYTHON_VERSION)" --link-mode "$(UV_LINK_MODE)"
	@set -eu; \
	if [ ! -x "$(VENV_PYTHON)" ]; then \
		echo "❌ Installation incomplète: $(VENV_PYTHON) est introuvable."; \
		exit 1; \
	fi; \
	echo "✅ Dépendances synchronisées avec uv."; \
	if [ -n "$(INSTALL_GOAL_REQUESTED)" ]; then \
		echo "Les cibles Makefile utilisent déjà le venv automatiquement."; \
		echo "Exemple :"; \
		echo "  make krpsim resources/ikea 10"; \
		echo "Option debug manuel : make shell"; \
	fi

# ------------------------------------------------------------
# Installe les binaires dans ~/.local/bin via symlinks (idempotent)
# ------------------------------------------------------------
install-bin: install
	@set -u; \
	if [ ! -d "$(VENV_DIR)" ]; then \
		echo "❌ Environnement uv introuvable. Lance d'abord: make install"; \
		exit 1; \
	fi; \
	VENV_PATH="$$(cd "$(VENV_DIR)" && pwd -P)"; \
	mkdir -p "$$HOME/.local/bin"; \
	for B in krpsim krpsim_verif; do \
		SRC="$$VENV_PATH/bin/$$B"; \
		DST="$$HOME/.local/bin/$$B"; \
		if [ -x "$$SRC" ]; then \
			if [ -L "$$DST" ] && [ "$$(readlink -f "$$DST" 2>/dev/null || true)" = "$$SRC" ]; then \
				echo "≡ Lien déjà correct: $$DST -> $$SRC"; \
			else \
				if ln -sf "$$SRC" "$$DST" 2>/dev/null; then \
					echo "🔗 $$DST -> $$SRC"; \
				else \
					echo "⚠️  Lien utilisateur ignoré pour '$$B' (espace insuffisant dans $$HOME)."; \
					echo "   Le binaire reste disponible via: $(UV_RUN) $$B"; \
				fi; \
			fi; \
		else \
			echo "❌ Binaire '$$B' introuvable dans le venv: $$SRC"; \
			exit 1; \
		fi; \
	done; \
	echo "💡 Si les liens ont été créés, assure-toi que $$HOME/.local/bin est dans le PATH (make print-path)"

# Désinstalle les symlinks utilisateur si présents
uninstall-bin:
	@rm -f "$$HOME/.local/bin/krpsim" "$$HOME/.local/bin/krpsim_verif"

# ------------------------------------------------------------
# Qualité de code : lint et typage statique
# ------------------------------------------------------------
lint: install
	@echo "# Lint (ruff) + type-check (mypy)"
	$(UV_RUN) ruff check src tests
	$(UV_RUN) mypy src tests

# ------------------------------------------------------------
# Mise en forme automatique du code
# ------------------------------------------------------------
PY_FILES := $(wildcard $(shell git ls-files '*.py'))

format: install
	@set -e; \
	if [ -n "$(PY_FILES)" ]; then \
		echo "# Format (black + isort)"; \
		$(UV_RUN) black $(PY_FILES); \
		$(UV_RUN) isort $(PY_FILES); \
	else \
		echo "Aucun fichier Python détecté via git ls-files."; \
	fi

# ------------------------------------------------------------
# Tests
# ------------------------------------------------------------
test: install
	$(UV_RUN) pytest

# ------------------------------------------------------------
# Exécutions (via uv)
# ------------------------------------------------------------
krpsim: install
	@set -u; \
	HAS_ERROR=0; \
	CYCLE_IS_INT=1; \
	if [ "$(KRPSIM_ARGS_COUNT)" -ne 2 ]; then \
		echo "[KRPSIM][ERREUR] Arguments invalides."; \
		echo "Usage: make krpsim <resource_file> <max_cycles>"; \
		echo "Exemple: make krpsim resources/simple 10"; \
		echo "Action: fournis exactement 2 arguments."; \
		HAS_ERROR=1; \
	fi; \
	if [ "$$HAS_ERROR" -eq 1 ]; then \
		exit 0; \
	fi; \
	if [ ! -f "$(KRPSIM_INPUT)" ]; then \
		echo "[KRPSIM][ERREUR] Fichier de configuration introuvable: $(KRPSIM_INPUT)"; \
		echo "Action: vérifie le chemin du fichier (ex: resources/simple)."; \
		HAS_ERROR=1; \
	fi; \
	case "$(KRPSIM_CYCLES)" in \
		''|*[!0-9]*) \
			echo "[KRPSIM][ERREUR] <max_cycles> doit etre un entier positif."; \
			echo "Valeur reçue: $(KRPSIM_CYCLES)"; \
			echo "Action: utilise un entier positif."; \
			CYCLE_IS_INT=0; \
			HAS_ERROR=1; \
			;; \
	esac; \
	if [ "$$CYCLE_IS_INT" -eq 1 ] && [ "$(KRPSIM_CYCLES)" -le 0 ]; then \
		echo "[KRPSIM][ERREUR] <max_cycles> doit etre strictement supérieur a 0."; \
		echo "Valeur reçue: $(KRPSIM_CYCLES)"; \
		echo "Action: utilise une valeur comme 1, 10, 100."; \
		HAS_ERROR=1; \
	fi; \
	if [ "$$HAS_ERROR" -eq 1 ]; then \
		exit 0; \
	fi; \
	CONFIG_BASENAME="$$(basename "$(KRPSIM_INPUT)")"; \
	CONFIG_STEM="$${CONFIG_BASENAME%.*}"; \
	TRACE_FILE="trace_$${CONFIG_STEM}.txt"; \
	echo "[KRPSIM] Exécution: file=$(KRPSIM_INPUT), max_cycles=$(KRPSIM_CYCLES)"; \
	echo "[KRPSIM] Trace de sortie: $$TRACE_FILE"; \
	OUT="$$(mktemp)"; \
	if $(UV_RUN) krpsim "$(KRPSIM_INPUT)" "$(KRPSIM_CYCLES)" --trace "$$TRACE_FILE" >"$$OUT" 2>&1; then \
		cat "$$OUT"; \
	else \
		CODE=$$?; \
		if grep -q "^invalid config:" "$$OUT"; then \
			REASON="$$(grep -m1 "^invalid config:" "$$OUT" | sed 's/^invalid config:[[:space:]]*//')"; \
			echo "[KRPSIM][ERREUR] Configuration invalide: $$REASON"; \
			echo "Action: corrige $(KRPSIM_INPUT) (format, doublons, ressources), puis relance."; \
		elif grep -q "Max time reached at time" "$$OUT"; then \
			DETAIL="$$(grep -m1 "Max time reached at time" "$$OUT")"; \
			echo "[KRPSIM][ERREUR] Limite de cycles atteinte."; \
			echo "Détail: $$DETAIL"; \
			echo "Action: augmente <max_cycles> ou ajuste la config pour converger."; \
		elif grep -q "Deadlock detected at time" "$$OUT"; then \
			DETAIL="$$(grep -m1 "Deadlock detected at time" "$$OUT")"; \
			echo "[KRPSIM][ERREUR] Deadlock détecté."; \
			echo "Détail: $$DETAIL"; \
			echo "Action: vérifie les dépendances de ressources/processus."; \
		else \
			echo "[KRPSIM][ERREUR] L'exécution a échoué (code=$$CODE)."; \
			echo "Action: vérifie la configuration et les arguments puis relance."; \
		fi; \
		echo "Détail technique:"; \
		sed 's/^/  /' "$$OUT"; \
	fi; \
	rm -f "$$OUT"

krpsim_verif: install
	@set -u; \
	HAS_ERROR=0; \
	if [ "$(KRPSIM_ARGS_COUNT)" -ne 2 ]; then \
		echo "[KRPSIM_VERIF][ERREUR] Arguments invalides."; \
		echo "Usage: make krpsim_verif <resource_file> <trace_file>"; \
		echo "Exemple: make krpsim_verif resources/simple trace.txt"; \
		echo "Action: fournis exactement 2 arguments."; \
		HAS_ERROR=1; \
	fi; \
	if [ "$$HAS_ERROR" -eq 1 ]; then \
		exit 0; \
	fi; \
	if [ ! -f "$(KRPSIM_VERIF_INPUT)" ]; then \
		echo "[KRPSIM_VERIF][ERREUR] Fichier de configuration introuvable: $(KRPSIM_VERIF_INPUT)"; \
		echo "Action: vérifie le chemin du fichier (ex: resources/simple)."; \
		HAS_ERROR=1; \
	fi; \
	if [ ! -f "$(KRPSIM_VERIF_TRACE)" ]; then \
		echo "[KRPSIM_VERIF][ERREUR] Fichier de trace introuvable: $(KRPSIM_VERIF_TRACE)"; \
		echo "Action: génère d'abord une trace puis relance la vérification."; \
		HAS_ERROR=1; \
	fi; \
	if [ "$$HAS_ERROR" -eq 1 ]; then \
		exit 0; \
	fi; \
	echo "[KRPSIM_VERIF] Vérification: file=$(KRPSIM_VERIF_INPUT), trace=$(KRPSIM_VERIF_TRACE)"; \
	OUT="$$(mktemp)"; \
	if $(UV_RUN) krpsim_verif "$(KRPSIM_VERIF_INPUT)" "$(KRPSIM_VERIF_TRACE)" >"$$OUT" 2>&1; then \
		cat "$$OUT"; \
	else \
		CODE=$$?; \
		echo "[KRPSIM_VERIF][ERREUR] L'exécution a échoué (code=$$CODE)."; \
		echo "Action: vérifie le format de la trace et la cohérence avec le fichier source."; \
		echo "Détail technique:"; \
		sed 's/^/  /' "$$OUT"; \
	fi; \
	rm -f "$$OUT"

# ------------------------------------------------------------
# Traitement en batch de toutes les ressources (silencieux, tout dans log.txt)
# ------------------------------------------------------------
process_resources: install
	@LOG="log.txt"; \
	: > "$$LOG"; \
	{ \
	  echo "=== Début du traitement de toutes les ressources — $$(date -Iseconds) ==="; \
	  files=$$(find resources -type f 2>/dev/null | sort); \
	  if [ -z "$$files" ]; then \
	    echo "Aucun fichier trouvé dans resources/"; \
	    echo "=== Terminé — $$(date -Iseconds) ==="; \
	  else \
	    set +e; \
	    for f in $$files; do \
	      echo "=== Traitement de $$f ==="; \
	      $(UV_RUN) krpsim "$$f" 10 || echo "⚠️  Échec krpsim sur $$f"; \
	      echo "=== Vérification de $$f ==="; \
	      $(UV_RUN) krpsim_verif "$$f" trace.txt || echo "⚠️  Échec krpsim_verif sur $$f"; \
	      echo ""; \
	      sleep 1; \
	    done; \
	    set -e; \
	    echo "=== Traitement terminé — $$(date -Iseconds) ==="; \
	  fi; \
	} >> "$$LOG" 2>&1

shell venv-shell: install
	@set -eu; \
	if [ ! -d "$(VENV_DIR)" ]; then \
		echo "❌ Environnement uv introuvable."; \
		echo "   Action: lance d'abord 'make install'."; \
		exit 1; \
	fi; \
	VENV_PATH="$$(cd "$(VENV_DIR)" && pwd -P)"; \
	if [ ! -f "$$VENV_PATH/bin/activate" ]; then \
		echo "❌ Script d'activation introuvable: $$VENV_PATH/bin/activate"; \
		echo "   Action: relance 'make install'."; \
		exit 1; \
	fi; \
	if [ ! -t 0 ]; then \
		echo "❌ 'make shell' doit être lancé depuis un terminal interactif."; \
		exit 1; \
	fi; \
	echo "Shell virtuel: $$VENV_PATH"; \
	echo "Tape 'deactivate' pour désactiver le venv, ou 'exit' pour revenir au shell précédent."; \
	if command -v bash >/dev/null 2>&1; then \
		RC_FILE="$$(mktemp)"; \
		printf '%s\n' \
			'[ -f "$$HOME/.bashrc" ] && . "$$HOME/.bashrc"' \
			". \"$$VENV_PATH/bin/activate\"" > "$$RC_FILE"; \
		bash --rcfile "$$RC_FILE" -i; \
		STATUS="$$?"; \
		rm -f "$$RC_FILE"; \
		exit "$$STATUS"; \
	fi; \
	. "$$VENV_PATH/bin/activate"; \
	exec "$${SHELL:-/bin/sh}" -i

# -------------------------------------------------------------------
# Uninstall / Clean / Fclean / Re
# -------------------------------------------------------------------
uninstall: uninstall-bin
	@set -eu; \
	if [ -e "$(VENV_DIR)" ]; then \
		rm -rf "$(VENV_DIR)"; \
		echo "✅ Environnement uv supprimé: $(VENV_DIR)"; \
	else \
		echo "Environnement uv déjà absent: $(VENV_DIR)"; \
	fi

clean:
	@rm -rf \
	  build dist \
	  .pytest_cache .mypy_cache \
	  .coverage coverage.xml htmlcov \
	  .ruff_cache .tox \
	  **/__pycache__ \
	  log.txt trace.txt trace_*.txt junit.xml \
	  .artifacts 2>/dev/null || true

fclean:
	@echo "🧹 Nettoyage"
	@$(MAKE) clean
	@$(MAKE) uninstall


re:
	@$(MAKE) fclean
	@$(MAKE) default

# ------------------------------------------------------------
# Outils debug
# ------------------------------------------------------------
which-bin:
	@set -e; \
	echo "Environnement uv du projet:"; \
	if [ -x "$(VENV_PYTHON)" ]; then \
		"$(VENV_PYTHON)" -c 'import sys; print(sys.prefix)'; \
	else \
		echo "(environnement non installé)"; \
	fi; \
	echo; \
	echo "which krpsim:"; which krpsim || echo "(non trouvé dans le PATH)"; \
	echo; \
	echo "ls ~/.local/bin:"; ls -l "$$HOME/.local/bin" 2>/dev/null || echo "(~/.local/bin inexistant)"

print-path:
	@echo "PATH = $$PATH"

doctor: ensure-uv
	@set -eu; \
	STATUS=0; \
	echo "— Doctor —"; \
	UV_VERSION="$$("$(UV_BIN)" --version 2>&1)"; \
	echo "uv: OK ($$UV_VERSION, $(UV_BIN))"; \
	PYTHON_PATH="$$("$(UV_BIN)" python find --no-python-downloads "$(PINNED_PYTHON_VERSION)" 2>/dev/null || true)"; \
	if [ -n "$$PYTHON_PATH" ] && [ -x "$$PYTHON_PATH" ]; then \
		echo "Python: OK ($$("$$PYTHON_PATH" --version 2>&1), $$PYTHON_PATH)"; \
	else \
		echo "Python $(PINNED_PYTHON_VERSION): ABSENT"; \
		STATUS=1; \
	fi; \
	if "$(UV_BIN)" lock --check >/dev/null 2>&1; then \
		echo "uv.lock: OK"; \
	else \
		echo "uv.lock: ABSENT ou obsolète"; \
		STATUS=1; \
	fi; \
	if [ -x "$(VENV_PYTHON)" ]; then \
		echo "Venv: OK ($$(cd "$(VENV_DIR)" && pwd -P))"; \
	else \
		echo "Venv: ABSENT"; \
		STATUS=1; \
	fi; \
	if command -v krpsim >/dev/null 2>&1; then \
		echo "krpsim dans PATH: $$(command -v krpsim)"; \
	else \
		echo "krpsim dans PATH: NON (lance make install-bin)"; \
	fi; \
	echo "——————"; \
	exit "$$STATUS"

help:
	@echo "Cibles :"
	@echo "  (défaut)      -> synchronise le projet dans .venv"
	@echo "  install       -> synchronise uv.lock dans .venv avec Python $(PINNED_PYTHON_VERSION)"
	@echo "  install-bin   -> symlinks vers ~/.local/bin (idempotent)"
	@echo "  uninstall-bin -> supprime les symlinks utilisateur"
	@echo "  shell         -> ouvre un shell interactif dans le venv"
	@echo "  krpsim <file> <cycles>          -> exécute via uv"
	@echo "    sortie: trace_<file>.txt"
	@echo "  krpsim_verif <file> <trace>     -> exécute via uv"
	@echo "  note          -> si un argument commence par '-', utilise: make -- <target> ..."
	@echo "  lint | format | test | process_resources"
	@echo "  clean | fclean | re | uninstall (supprime .venv et les liens)"
	@echo "  doctor        -> vérifie uv, Python, uv.lock et l'environnement"
	@echo "  which-bin | print-path | help"
