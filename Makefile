# Makefile pour automatiser l'installation, le linting,
# le formatage, les tests et l'exécution de krpsim
#
# Usage express :
#   make                -> install + install-bin
#   krpsim --help       -> dispo direct si ~/.local/bin est dans le PATH

.PHONY: default install install-bin uninstall-bin \
        lint format test krpsim krpsim_verif process_resources \
        clean fclean re uninstall which-bin print-path help doctor \
			show-activate

MAKEFLAGS += --no-print-directory
POETRY_BIN = $(shell command -v poetry 2>/dev/null || printf '%s' "$(HOME)/.local/bin/poetry")
POETRY = $(POETRY_BIN) run
POETRY_INSTALL_URL = https://install.python-poetry.org
VENV_DIR = .venv

# ------------------------------------------------------------
# [DEFAULT] Installation complète (deps + binaires user)
# ------------------------------------------------------------
default: install install-bin
	@echo "✅ Installation terminée. 'krpsim' est utilisable directement."
	@echo "   Ex.: krpsim --help"

# ------------------------------------------------------------
# INSTALL avec cache basé sur .venv :
# Relance l'installation si pyproject.toml/poetry.lock sont plus récents.
# ------------------------------------------------------------
$(VENV_DIR): pyproject.toml poetry.lock
	@echo "# Vérification des dépendances (cache .venv)…"
	@set -eu; \
	if [ ! -d "$(VENV_DIR)" ]; then \
		echo "# Environnement virtuel absent : installation initiale"; \
	fi; \
	POETRY_BIN="$(POETRY_BIN)"; \
	if [ ! -x "$$POETRY_BIN" ]; then \
		echo "# Poetry introuvable dans la session : installation automatique (sans sudo)."; \
		if ! command -v curl >/dev/null 2>&1; then \
			echo "❌ 'curl' est requis pour installer Poetry automatiquement."; \
			echo "   Action: installe curl ou installe Poetry manuellement via $(POETRY_INSTALL_URL)."; \
			exit 1; \
		fi; \
		if ! command -v python3 >/dev/null 2>&1; then \
			echo "❌ 'python3' est requis pour installer Poetry automatiquement."; \
			echo "   Action: installe Python 3 puis relance 'make install'."; \
			exit 1; \
		fi; \
		if ! curl -sSL "$(POETRY_INSTALL_URL)" | python3 -; then \
			echo "❌ L'installation automatique de Poetry a échoué."; \
			echo "   Action: vérifie la connexion réseau, puis relance 'make install'."; \
			exit 1; \
		fi; \
		POETRY_BIN="$$HOME/.local/bin/poetry"; \
		if [ ! -x "$$POETRY_BIN" ]; then \
			echo "❌ Poetry semble installé mais binaire introuvable: $$POETRY_BIN"; \
			echo "   Action: ajoute $$HOME/.local/bin au PATH puis relance 'make install'."; \
			exit 1; \
		fi; \
		POETRY_VERSION="$$( "$$POETRY_BIN" --version 2>/dev/null || true )"; \
		[ -n "$$POETRY_VERSION" ] && echo "✅ $$POETRY_VERSION"; \
	fi; \
	echo "# Installation des dépendances et du package"; \
	"$$POETRY_BIN" install; \
	touch "$(VENV_DIR)"; \
	echo "✅ Dépendances installées."


install: $(VENV_DIR)

# ------------------------------------------------------------
# Installe les binaires dans ~/.local/bin via symlinks (idempotent)
# ------------------------------------------------------------
install-bin: install
	@set -eu; \
	POETRY_BIN="$(POETRY_BIN)"; \
	VENV_PATH="$$( "$$POETRY_BIN" env info -p 2>/dev/null || true )"; \
	if [ -z "$$VENV_PATH" ] || [ ! -d "$$VENV_PATH" ]; then \
		echo "❌ Venv Poetry introuvable. Lance d'abord: make install"; \
		exit 1; \
	fi; \
	mkdir -p "$$HOME/.local/bin"; \
	for B in krpsim krpsim_verif; do \
		SRC="$$VENV_PATH/bin/$$B"; \
		DST="$$HOME/.local/bin/$$B"; \
		if [ -x "$$SRC" ]; then \
			if [ -L "$$DST" ] && [ "$$(readlink -f "$$DST" 2>/dev/null || true)" = "$$SRC" ]; then \
				echo "≡ Lien déjà correct: $$DST -> $$SRC"; \
			else \
				ln -sf "$$SRC" "$$DST"; \
				echo "🔗 $$DST -> $$SRC"; \
			fi; \
		else \
			echo "⚠️  Binaire '$$B' introuvable dans le venv (??)"; \
		fi; \
	done; \
	echo "💡 Assure-toi que $$HOME/.local/bin est dans le PATH (make print-path)"

# Désinstalle les symlinks utilisateur si présents
uninstall-bin:
	@set -eu; \
	rm -f "$$HOME/.local/bin/krpsim" "$$HOME/.local/bin/krpsim_verif"; \

# ------------------------------------------------------------
# Qualité de code : lint et typage statique
# ------------------------------------------------------------
lint: install
	@echo "# Lint (ruff) + type-check (mypy)"
	$(POETRY) ruff check src tests || true
	$(POETRY) mypy src tests || true

# ------------------------------------------------------------
# Mise en forme automatique du code
# ------------------------------------------------------------
PY_FILES := $(shell git ls-files '*.py')

format: install
	@if [ -n "$(PY_FILES)" ]; then \
		echo "# Format (black + isort)"; \
		$(POETRY) black $(PY_FILES) || true; \
		$(POETRY) isort $(PY_FILES) || true; \
	else \
		echo "Aucun fichier Python détecté via git ls-files."; \
	fi

# ------------------------------------------------------------
# Tests
# ------------------------------------------------------------
test: install
	$(POETRY) pytest || true

# ------------------------------------------------------------
# Exécutions (via Poetry)
# ------------------------------------------------------------
krpsim: install
	@set -euo pipefail; \
	file = "$(word 1,$(MAKECMDGOALS))"; \
	echo "⚡ Exécution de krpsim sur $$file"; \
	$(POETRY) krpsim $(filter-out $@,$(MAKECMDGOALS))
	exit 0;

krpsim_verif: install
	$(POETRY) krpsim_verif $(filter-out $@,$(MAKECMDGOALS))

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
	      $(POETRY) krpsim "$$f" 10 || echo "⚠️  Échec krpsim sur $$f"; \
	      echo "=== Vérification de $$f ==="; \
	      $(POETRY) krpsim_verif "$$f" trace.txt || echo "⚠️  Échec krpsim_verif sur $$f"; \
	      echo ""; \
	      sleep 1; \
	    done; \
	    set -e; \
	    echo "=== Traitement terminé — $$(date -Iseconds) ==="; \
	  fi; \
	} >> "$$LOG" 2>&1

show-activate:
	@echo "Commande d'activation (a executer dans le shell courant) :"
	@echo "source $$(poetry env info -p)/bin/activate"

# -------------------------------------------------------------------
# Uninstall / Clean / Fclean / Re
# -------------------------------------------------------------------
uninstall:
	@set -eu; \
	POETRY_BIN="$(POETRY_BIN)"; \
	if [ -x "$$POETRY_BIN" ] && "$$POETRY_BIN" env info -p >/dev/null 2>&1; then \
		echo "🧽 Skip désinstallation du package (sera supprimé avec le venv)."; \
	fi

clean:
	@rm -rf \
	  build dist \
	  .pytest_cache .mypy_cache \
	  .coverage coverage.xml htmlcov \
	  .ruff_cache .tox \
	  **/__pycache__ \
	  log.txt trace.txt junit.xml \
	  .artifacts docs/graphs 2>/dev/null || true

fclean:
	@echo "🧹 Nettoyage"
	@$(MAKE) clean
	@$(MAKE) uninstall
	@{ \
		set -eu; \
		POETRY_BIN="$(POETRY_BIN)"; \
		VENV_PATH="$$( "$$POETRY_BIN" env info -p 2>/dev/null || true )"; \
		: # 1) Suppression via Poetry par chemin (plus fiable); \
		if [ -n "$$VENV_PATH" ]; then \
			"$$POETRY_BIN" env remove "$$VENV_PATH" >/dev/null 2>&1 || true; \
		fi; \
		: # 2) Fallback: si le dossier existe encore, on l'enlève; \
		if [ -n "$$VENV_PATH" ] && [ -d "$$VENV_PATH" ]; then \
			rm -rf "$$VENV_PATH"; \
		fi; \
		: # 3) Fallback additionnel: cas in-project .venv; \
		if [ -d ".venv" ]; then \
			rm -rf ".venv"; \
		fi; \
		}; true
	@$(MAKE) uninstall-bin
	@set -eu; \
	POETRY_LINK="$$HOME/.local/bin/poetry"; \
	POETRY_HOME="$$HOME/.local/share/pypoetry"; \
	if [ -L "$$POETRY_LINK" ] && [ ! -x "$$POETRY_LINK" ] && [ ! -d "$$POETRY_HOME" ]; then \
		echo "# Nettoyage d'un symlink Poetry cassé: $$POETRY_LINK"; \
		rm -f "$$POETRY_LINK"; \
		echo "✅ Symlink Poetry cassé supprimé."; \
	elif [ -x "$$POETRY_LINK" ] || [ -d "$$POETRY_HOME" ]; then \
		echo "# Désinstallation de Poetry utilisateur (~/.local)"; \
		if ! command -v curl >/dev/null 2>&1; then \
			echo "❌ Impossible de désinstaller Poetry automatiquement: 'curl' est absent."; \
			echo "   Action: installe curl, ou lance manuellement: curl -sSL $(POETRY_INSTALL_URL) | python3 - --uninstall"; \
			exit 1; \
		fi; \
		if ! command -v python3 >/dev/null 2>&1; then \
			echo "❌ Impossible de désinstaller Poetry automatiquement: 'python3' est absent."; \
			echo "   Action: installe Python 3, ou désinstalle Poetry manuellement."; \
			exit 1; \
		fi; \
		if ! curl -sSL "$(POETRY_INSTALL_URL)" | python3 - --uninstall; then \
			echo "❌ La désinstallation automatique de Poetry a échoué."; \
			echo "   Action: relance 'make fclean' avec Internet, ou exécute la commande manuelle d'uninstall."; \
			exit 1; \
		fi; \
		if [ -L "$$POETRY_LINK" ] && [ ! -e "$$POETRY_LINK" ]; then \
			rm -f "$$POETRY_LINK"; \
		fi; \
		if [ -L "$$POETRY_LINK" ] || [ -x "$$POETRY_LINK" ] || [ -d "$$POETRY_HOME" ]; then \
			echo "❌ Poetry semble encore présent dans ~/.local après désinstallation."; \
			echo "   Action: vérifie les permissions puis supprime ~/.local/bin/poetry et ~/.local/share/pypoetry."; \
			exit 1; \
		fi; \
		echo "✅ Poetry utilisateur supprimé."; \
	else \
		echo "# Poetry utilisateur déjà absent (rien à désinstaller)."; \
	fi


re:
	@$(MAKE) fclean
	@$(MAKE) default

# ------------------------------------------------------------
# Outils debug
# ------------------------------------------------------------
which-bin:
	@set -e; \
	echo "Poetry venv:"; \
	POETRY_BIN="$(POETRY_BIN)"; \
	if [ -x "$$POETRY_BIN" ]; then "$$POETRY_BIN" env info -p || true; else echo "(poetry non installé)"; fi; \
	echo; \
	echo "which krpsim:"; which krpsim || echo "(non trouvé dans le PATH)"; \
	echo; \
	echo "ls ~/.local/bin:"; ls -l "$$HOME/.local/bin" 2>/dev/null || echo "(~/.local/bin inexistant)"

print-path:
	@echo "PATH = $$PATH"

doctor:
	@set -eu; \
	POETRY_BIN="$(POETRY_BIN)"; \
	echo "— Doctor —"; \
	[ -x "$$POETRY_BIN" ] && echo "Poetry: OK ($$POETRY_BIN)" || echo "Poetry: ABSENT"; \
	if [ -x "$$POETRY_BIN" ]; then \
		VENV="$$( "$$POETRY_BIN" env info -p 2>/dev/null || true )"; \
		[ -n "$$VENV" ] && echo "Venv: $$VENV" || echo "Venv: ABSENT"; \
	fi; \
	which krpsim >/dev/null 2>&1 && echo "krpsim dans PATH: $$([ -n "$$(which krpsim 2>/dev/null)" ] && which krpsim)" || echo "krpsim dans PATH: NON"; \
	[ -d "$(VENV_DIR)" ] && echo "Dossier venv présent: $(VENV_DIR)" || echo "Dossier venv: ABSENT"; \
	echo "——————"

help:
	@echo "Cibles :"
	@echo "  (défaut)      -> install + install-bin"
	@echo "  install       -> auto-installe Poetry si absent, puis installe les deps"
	@echo "  install-bin   -> symlinks vers ~/.local/bin (idempotent)"
	@echo "  uninstall-bin -> supprime les symlinks utilisateur"
	@echo "  krpsim ...    -> exécute via Poetry"
	@echo "  krpsim_verif  -> exécute via Poetry"
	@echo "  lint | format | test | process_resources"
	@echo "  clean | fclean (supprime aussi Poetry user) | re | uninstall"
	@echo "  which-bin | print-path | doctor | help"
