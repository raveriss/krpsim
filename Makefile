.DEFAULT_GOAL := install
.PHONY: install krpsim krpsim_verif clean fclean

UV_BIN ?= $(shell command -v uv 2>/dev/null || printf '%s' "$(HOME)/.local/bin/uv")
export UV_LINK_MODE ?= copy
export UV_PYTHON := $(file <.python-version)
export UV_PYTHON_DOWNLOADS := automatic
export UV_PROJECT_ENVIRONMENT := $(CURDIR)/.venv
ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))

install:
	@if [ ! -x "$(UV_BIN)" ]; then \
		installer=$$(curl -LsSf https://astral.sh/uv/install.sh) && \
		UV_UNMANAGED_INSTALL="$(dir $(UV_BIN))" sh -c "$$installer"; \
	fi
	@if [ ! -x .venv/bin/python ] || [ "$$("$(UV_BIN)" python find)" != "$(UV_PROJECT_ENVIRONMENT)/bin/python" ]; then \
		"$(UV_BIN)" venv --allow-existing .venv; \
	fi
	@"$(UV_BIN)" sync --locked

krpsim krpsim_verif: install
	@.venv/bin/$@ $(foreach arg,$(ARGS),'$(subst ','"'"',$(arg))') \
		$(if $(filter krpsim,$@),--trace '$(subst ','"'"',trace_$(basename $(notdir $(firstword $(ARGS)))).txt)')

clean:
	@rm -rf build dist .pytest_cache .mypy_cache .coverage coverage.xml htmlcov \
		.ruff_cache .tox **/__pycache__ log.txt trace.txt trace_*.txt junit.xml .artifacts

fclean: clean
	@rm -rf .venv

# Les arguments positionnels ne sont pas des commandes Make.
ifneq (,$(filter $(firstword $(MAKECMDGOALS)),krpsim krpsim_verif))
.PHONY: $(ARGS)
$(ARGS):; @:
endif
