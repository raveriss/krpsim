# Makefile pour automatiser l'installation, le linting,
# le formatage, les tests et l'exécution de krpsim
#
# Usage express :
#   make                -> install + install-bin
#   krpsim --help       -> dispo direct si ~/.local/bin est dans le PATH

.PHONY: default install install-bin uninstall-bin \
        lint format test krpsim krpsim_verif graph process_resources \
        clean fclean re uninstall which-bin print-path help doctor \
		show-activate

MAKEFLAGS += --no-print-directory
POETRY_BIN = $(shell command -v poetry 2>/dev/null || printf '%s' "$(HOME)/.local/bin/poetry")
POETRY = $(POETRY_BIN) run
POETRY_INSTALL_URL = https://install.python-poetry.org
VENV_DIR = .venv
KRPSIM_INPUT = $(word 2,$(MAKECMDGOALS))
KRPSIM_CYCLES = $(word 3,$(MAKECMDGOALS))
KRPSIM_VERIF_INPUT = $(word 2,$(MAKECMDGOALS))
KRPSIM_VERIF_TRACE = $(word 3,$(MAKECMDGOALS))
KRPSIM_ARGS_COUNT = $(words $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS)))
CLI_ARG_TARGETS = krpsim krpsim_verif

ifneq (,$(filter $(firstword $(MAKECMDGOALS)),$(CLI_ARG_TARGETS)))
CLI_ARGS = $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
.PHONY: $(CLI_ARGS)
$(foreach arg,$(CLI_ARGS),$(eval $(arg):;@:))
endif

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
	@echo "# Installation de l'Environnement virtuel des dépendances et du package"
	@set -eu; \
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
	GRAPH_CONFIG_FILE="graph_config_$${CONFIG_STEM}.json"; \
	echo "[KRPSIM] Exécution: file=$(KRPSIM_INPUT), max_cycles=$(KRPSIM_CYCLES)"; \
	echo "[KRPSIM] Trace de sortie: $$TRACE_FILE"; \
	echo "[KRPSIM] Config graphe: $$GRAPH_CONFIG_FILE"; \
	OUT="$$(mktemp)"; \
	if $(POETRY) krpsim "$(KRPSIM_INPUT)" "$(KRPSIM_CYCLES)" --trace "$$TRACE_FILE" >"$$OUT" 2>&1; then \
		cat "$$OUT"; \
		CFG_OUT="$$(mktemp)"; \
		if $(POETRY) python gantt_project/build_graph_config.py \
			--config "$(KRPSIM_INPUT)" \
			--trace "$$TRACE_FILE" \
			--output "$$GRAPH_CONFIG_FILE" >"$$CFG_OUT" 2>&1; then \
			[ -s "$$CFG_OUT" ] && cat "$$CFG_OUT"; \
		else \
			CFG_CODE=$$?; \
			echo "[KRPSIM][ERREUR] Génération de la config graphe échouée (code=$$CFG_CODE)."; \
			echo "Action: vérifie le fichier de config, la trace, puis relance la commande."; \
			echo "Détail technique:"; \
			sed 's/^/  /' "$$CFG_OUT"; \
		fi; \
		rm -f "$$CFG_OUT"; \
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
	if $(POETRY) krpsim_verif "$(KRPSIM_VERIF_INPUT)" "$(KRPSIM_VERIF_TRACE)" >"$$OUT" 2>&1; then \
		cat "$$OUT"; \
		CONFIG_BASENAME="$$(basename "$(KRPSIM_VERIF_INPUT)")"; \
		CONFIG_STEM="$${CONFIG_BASENAME%.*}"; \
		GRAPH_CONFIG_FILE="graph_config_$${CONFIG_STEM}.json"; \
		CFG_OUT="$$(mktemp)"; \
		if $(POETRY) python gantt_project/build_graph_config.py \
			--config "$(KRPSIM_VERIF_INPUT)" \
			--trace "$(KRPSIM_VERIF_TRACE)" \
			--output "$$GRAPH_CONFIG_FILE" >"$$CFG_OUT" 2>&1; then \
			[ -s "$$CFG_OUT" ] && cat "$$CFG_OUT"; \
			echo "[GRAPH] Génération du graphe Gantt"; \
			GRAPH_OUT="$$(mktemp)"; \
			if $(POETRY) python gantt_project/gantt.py --config "$$GRAPH_CONFIG_FILE" >"$$GRAPH_OUT" 2>&1; then \
				[ -s "$$GRAPH_OUT" ] && cat "$$GRAPH_OUT"; \
			else \
				GRAPH_CODE=$$?; \
				echo "[GRAPH][ERREUR] La génération a échoué (code=$$GRAPH_CODE)."; \
				echo "Action: vérifie le fichier $$GRAPH_CONFIG_FILE et les dépendances graphiques."; \
				echo "Détail technique:"; \
				sed 's/^/  /' "$$GRAPH_OUT"; \
			fi; \
			rm -f "$$GRAPH_OUT"; \
		else \
			CFG_CODE=$$?; \
			echo "[KRPSIM_VERIF][ERREUR] Génération de la config graphe échouée (code=$$CFG_CODE)."; \
			echo "Action: vérifie le fichier de config, la trace, puis relance la commande."; \
			echo "Détail technique:"; \
			sed 's/^/  /' "$$CFG_OUT"; \
		fi; \
		rm -f "$$CFG_OUT"; \
	else \
		CODE=$$?; \
		echo "[KRPSIM_VERIF][ERREUR] L'exécution a échoué (code=$$CODE)."; \
		echo "Action: vérifie le format de la trace et la cohérence avec le fichier source."; \
		echo "Détail technique:"; \
		sed 's/^/  /' "$$OUT"; \
	fi; \
	rm -f "$$OUT"

graph: install
	@echo "[GRAPH] Génération du graphe Gantt"; \
	OUT="$$(mktemp)"; \
	if $(POETRY) python gantt_project/gantt.py --config graph_config_simple.json >"$$OUT" 2>&1; then \
		cat "$$OUT"; \
	else \
		CODE=$$?; \
		echo "[GRAPH][ERREUR] La génération a échoué (code=$$CODE)."; \
		echo "Action: vérifie graph_config_simple.json, les dépendances graphiques et le script gantt_project/gantt.py."; \
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
	@set -eu; \
	POETRY_BIN="$(POETRY_BIN)"; \
	if [ ! -x "$$POETRY_BIN" ]; then \
		echo "❌ Poetry introuvable: $$POETRY_BIN"; \
		echo "   Action: lance d'abord 'make install'."; \
		exit 1; \
	fi; \
	VENV_PATH="$$( "$$POETRY_BIN" env info -p 2>/dev/null || true )"; \
	if [ -z "$$VENV_PATH" ] || [ ! -d "$$VENV_PATH" ]; then \
		echo "❌ Environnement Poetry introuvable."; \
		echo "   Action: lance d'abord 'make install'."; \
		exit 1; \
	fi; \
	echo "Commande d'activation (POSIX, compatible /bin/sh) :"; \
	echo ". \"$$VENV_PATH/bin/activate\""; \
	echo "Commande équivalente (bash/zsh) :"; \
	echo "source \"$$VENV_PATH/bin/activate\""

# -------------------------------------------------------------------
# Uninstall / Clean / Fclean / Re
# -------------------------------------------------------------------
uninstall:
	@set -eu; \
	POETRY_BIN="$(POETRY_BIN)"; \

clean:
	@rm -rf \
	  build dist \
	  .pytest_cache .mypy_cache \
	  .coverage coverage.xml htmlcov \
	  .ruff_cache .tox \
	  **/__pycache__ \
	  log.txt trace.txt trace_*.txt graph_config_*.json junit.xml \
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
		rm -rf .venv; \
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
	@echo "  krpsim <file> <cycles>          -> exécute via Poetry"
	@echo "    sortie: trace_<file>.txt + graph_config_<file>.json"
	@echo "  krpsim_verif <file> <trace>     -> exécute via Poetry"
	@echo "  note          -> si un argument commence par '-', utilise: make -- <target> ..."
	@echo "  graph         -> génère le graphe Gantt"
	@echo "  lint | format | test | process_resources"
	@echo "  clean | fclean (supprime aussi Poetry user) | re | uninstall"
	@echo "  which-bin | print-path | doctor | help"
