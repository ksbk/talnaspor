# Compatible with GNU Make 3.81 (including macOS's bundled make).
.DEFAULT_GOAL := help
.DELETE_ON_ERROR:

SHELL := /bin/sh
UV ?= uv
RUFF_ARGS ?=
PYTEST_ARGS ?=
MYPY_ARGS ?=
RUN_DEV = $(UV) run --locked --group dev

.PHONY: help sync run evaluate requirements requirements-check lock lock-check lint format format-check typecheck test check build clean clean-venv distclean

help: ## Show available commands (the default).
	@awk 'BEGIN { printf "Usage: make <target>\n\n" } /^[a-zA-Z_-]+:.*## / { split($$0, parts, "## "); sub(/:.*/, "", parts[1]); printf "  %-16s %s\n", parts[1], parts[2] }' $(MAKEFILE_LIST)

sync: ## Install the project and development tools from uv.lock.
	$(UV) sync --locked --group dev

run: ## Start the API at http://127.0.0.1:8000 (docs at /docs).
	$(UV) run --locked uvicorn talnaspor.app:app --reload

evaluate: ## Ask every evaluation question live; write evaluation/results.md.
	$(RUN_DEV) python scripts/evaluate.py

lock: ## Update uv.lock after changing dependencies.
	$(UV) lock

lock-check: ## Check that uv.lock matches pyproject.toml.
	$(UV) lock --check

EXPORT = $(UV) export --locked --no-dev --no-hashes --no-emit-project --format requirements-txt

requirements: ## Regenerate requirements.txt (pinned, for pip) from uv.lock.
	$(EXPORT) > requirements.txt

requirements-check: ## Check that requirements.txt matches uv.lock.
	$(EXPORT) | diff -q - requirements.txt >/dev/null || \
		{ echo "requirements.txt is out of date: run make requirements"; exit 1; }

lint: ## Check Python code with Ruff.
	$(RUN_DEV) ruff check . $(RUFF_ARGS)

format: ## Format Python code with Ruff.
	$(RUN_DEV) ruff format . $(RUFF_ARGS)

format-check: ## Check Python formatting without changing files.
	$(RUN_DEV) ruff format --check . $(RUFF_ARGS)

typecheck: ## Check source and test types with mypy.
	$(RUN_DEV) mypy $(MYPY_ARGS)

test: ## Run pytest (pass options with PYTEST_ARGS='...').
	$(RUN_DEV) pytest $(PYTEST_ARGS)

check: lock-check requirements-check lint format-check typecheck test ## Run dependency, lint, formatting, type, and test checks.

build: ## Build source and wheel distributions in dist/.
	$(UV) build

# No Python or uv installation is needed to clean. Do not follow symlinks,
# descend into virtual environments, or touch Git metadata. Prune matched
# directories before deleting them so find never visits removed children.
clean: ## Remove build outputs, Python/tool caches, and coverage reports; keep .venv.
	@find . -type d \( -name .git -o -name .venv -o -name venv -o -name env -o -name node_modules \) -prune -o \
		-type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache -o -name .mypy_cache -o -name .pytype -o -name .pyre -o -name '*.egg-info' \) -prune -exec rm -rf {} + -o \
		-type f \( -name '*.pyc' -o -name '*.pyo' -o -name .coverage -o -name '.coverage.*' \) -exec rm -f {} +
	@rm -rf -- build dist htmlcov .tox .nox
	@rm -f -- coverage.xml coverage.json
	@printf 'Removed build artifacts and caches (kept virtual environments).\n'

clean-venv: ## Remove the project's .venv; restore it with make sync.
	@rm -rf -- .venv
	@printf 'Removed .venv. Run make sync to recreate it.\n'

distclean: clean clean-venv ## Remove generated artifacts and .venv; keep uv.lock and .env.
