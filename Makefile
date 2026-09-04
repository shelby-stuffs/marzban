PYTHON ?= python3

.PHONY: install-uv setup setup-dev run run-cli migrate check-migrations check test format clean

install-uv:
	@command -v uv >/dev/null 2>&1 || $(PYTHON) -m pip install --user uv

setup: install-uv
	uv sync

setup-dev: install-uv
	uv sync --group dev

run:
	uv run python main.py

run-cli:
	uv run python marzban-cli.py

migrate:
	uv run alembic upgrade head

check-migrations:
	uv run alembic check

check:
	uv run ruff check .
	uv run python -m compileall -q app cli xray_api

test:
	uv run pytest

format:
	uv run ruff format .

clean:
	rm -rf .venv .pytest_cache .ruff_cache
