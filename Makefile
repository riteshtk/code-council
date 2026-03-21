.PHONY: install dev backend frontend db-migrate db-reset test test-backend test-frontend lint format demo docker-up docker-down

install:
	cd backend && uv pip install --system -e ".[dev]"
	cd frontend && npm install

dev:
	docker compose up -d postgres redis
	@echo "Waiting for PostgreSQL..."
	@sleep 3
	cd backend && alembic upgrade head
	@make -j2 backend frontend

backend:
	cd backend && uvicorn codecouncil.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

db-migrate:
	cd backend && alembic upgrade head

db-reset:
	cd backend && alembic downgrade base && alembic upgrade head

test: test-backend test-frontend

test-backend:
	cd backend && pytest -v --cov=codecouncil

test-frontend:
	cd frontend && npx vitest run

lint:
	cd backend && ruff check src/ tests/
	cd frontend && npx next lint

format:
	cd backend && ruff format src/ tests/
	cd frontend && npx prettier --write "src/**/*.{ts,tsx,css}"

demo:
	cd backend && codecouncil analyse https://github.com/tiangolo/fastapi --demo --stream

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
