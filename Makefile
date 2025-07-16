.PHONY: install lint format test run

install:
	poetry install

lint:
	poetry run ruff check src tests
	poetry run mypy src tests

format:
	poetry run black src tests
	poetry run isort src tests

test:
	poetry run pytest

ARGS ?=

run:
	poetry run krpsim $(ARGS)

