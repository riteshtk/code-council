.PHONY: install dev backend frontend db-migrate db-reset test test-backend test-frontend lint format demo docker-up docker-down venv

VENV := backend/.venv
ACTIVATE := . $(VENV)/bin/activate &&

venv:
	cd backend && python3 -m venv .venv
	$(ACTIVATE) pip install uv
	$(ACTIVATE) cd backend && uv pip install -e ".[dev]"

install: venv
	cd frontend && npm install

dev:
	docker compose up -d postgres redis
	@echo "Waiting for PostgreSQL..."
	@sleep 3
	$(ACTIVATE) cd backend && alembic upgrade head
	@make -j2 backend frontend

backend:
	$(ACTIVATE) cd backend && uvicorn codecouncil.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

db-migrate:
	$(ACTIVATE) cd backend && alembic upgrade head

db-reset:
	$(ACTIVATE) cd backend && alembic downgrade base && alembic upgrade head

test: test-backend test-frontend

test-backend:
	$(ACTIVATE) cd backend && pytest -v --cov=codecouncil

test-frontend:
	cd frontend && npx vitest run

lint:
	$(ACTIVATE) cd backend && ruff check src/ tests/
	cd frontend && npx next lint

format:
	$(ACTIVATE) cd backend && ruff format src/ tests/
	cd frontend && npx prettier --write "src/**/*.{ts,tsx,css}"

demo:
	$(ACTIVATE) cd backend && codecouncil analyse https://github.com/tiangolo/fastapi --demo --stream

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
