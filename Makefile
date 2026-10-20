.PHONY: help setup up down backend serving cdc demo test parity rebuild dagster lint fmt clean

PYTHON ?= python3.11
VENV ?= .venv
BIN = $(VENV)/bin

help:
	@echo "Mzigo: Last-Mile Delivery Platform with Change Data Capture"
	@echo "==========================================================="
	@echo "Available commands:"
	@echo "  make setup     - Create virtual environment and install dependencies"
	@echo "  make up        - Start Docker services (Postgres/PostGIS, Kafka, Debezium)"
	@echo "  make down      - Stop Docker services"
	@echo "  make backend   - Run FastAPI write API on port 8000"
	@echo "  make serving   - Run FastAPI read serving API on port 8002"
	@echo "  make cdc       - Run CDC consumer (stream Bronze & Silver Delta tables)"
	@echo "  make demo      - Run full end-to-end simulated delivery lifecycle and CDC demo"
	@echo "  make test      - Run all unit, integration, and chaos tests"
	@echo "  make parity    - Run Postgres-to-Silver row-count and row-hash parity check"
	@echo "  make rebuild   - Drop Silver and Gold, recreate from Bronze, and verify parity"
	@echo "  make dagster   - Launch Dagster webserver and daemon"
	@echo "  make lint      - Run ruff linter"
	@echo "  make fmt       - Format Python source files"
	@echo "  make clean     - Clean local Delta tables, databases, logs, and caches"

setup:
	@if command -v uv >/dev/null 2>&1; then \
		uv venv --python $(PYTHON) $(VENV); \
		uv pip install --python $(BIN)/python -e ".[dev]"; \
	else \
		$(PYTHON) -m venv $(VENV); \
		$(BIN)/pip install --upgrade pip; \
		$(BIN)/pip install -e ".[dev]"; \
	fi
	@if [ -f $(BIN)/pre-commit ]; then $(BIN)/pre-commit install; fi
	@echo "Setup complete. Activate environment with: source $(VENV)/bin/activate"

up:
	docker compose up -d
	@echo "Waiting for PostgreSQL to become healthy..."
	@until docker compose exec -T postgres pg_isready -U mzigo_user -d mzigo >/dev/null 2>&1; do \
		sleep 1; \
	done
	@echo "Postgres + PostGIS ready on port 5432."
	@echo "Waiting for Debezium Kafka Connect..."
	@until curl -sf http://localhost:8083/connectors >/dev/null 2>&1; do \
		sleep 2; \
	done
	@echo "Registering Debezium Postgres connector..."
	@curl -s -X POST -H "Content-Type: application/json" --data @cdc/debezium/connector.json http://localhost:8083/connectors || true
	@echo ""
	@echo "Mzigo CDC services are online."

down:
	docker compose down

backend:
	$(BIN)/uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload

serving:
	$(BIN)/uvicorn serving.app:app --host 0.0.0.0 --port 8002 --reload

cdc:
	$(BIN)/python -m cdc.consumer.main

demo:
	$(BIN)/python -m simulator.cli demo

test:
	$(BIN)/pytest tests/

parity:
	$(BIN)/python -m cdc.consumer.parity

rebuild:
	$(BIN)/python -m cdc.consumer.rebuild

dagster:
	$(BIN)/dagster dev -f orchestration/definitions.py

lint:
	$(BIN)/ruff check .

fmt:
	$(BIN)/ruff format .

clean:
	rm -rf data/ delta/ *.duckdb* checkpoints/ .pytest_cache/ .ruff_cache/ *.log
