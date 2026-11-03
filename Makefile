PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin

.PHONY: help venv install lint format typecheck test run examples

help:
	@echo "make install    — venv и зависимости"
	@echo "make lint       — ruff"
	@echo "make format     — ruff format и автоисправления"
	@echo "make typecheck  — mypy"
	@echo "make test       — pytest"
	@echo "make run        — черновик первого товара в stdout"
	@echo "make examples   — черновики двух товаров в examples/"

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(BIN)/pip install -e ".[dev]"

lint:
	$(BIN)/ruff check app tests
	$(BIN)/ruff format --check app tests

format:
	$(BIN)/ruff format app tests
	$(BIN)/ruff check --fix app tests

typecheck:
	$(BIN)/mypy app

test:
	$(BIN)/pytest

run:
	$(BIN)/python -m app.cli fixtures/cem-dt-8890a.json

examples:
	$(BIN)/python -m app.cli fixtures/cem-dt-8890a.json --output examples/cem-dt-8890a.md --json-output examples/cem-dt-8890a.json
	$(BIN)/python -m app.cli fixtures/cem-dt-8897.json --output examples/cem-dt-8897.md --json-output examples/cem-dt-8897.json
