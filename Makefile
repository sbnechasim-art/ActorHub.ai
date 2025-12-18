# ActorHub.ai Makefile
# Common development commands

.PHONY: help setup dev build test clean docker-up docker-down migrate

help:
	@echo "ActorHub.ai Development Commands"
	@echo ""
	@echo "  make setup      - Setup development environment"
	@echo "  make dev        - Start all development servers"
	@echo "  make build      - Build all packages"
	@echo "  make test       - Run all tests"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make docker-up  - Start Docker services"
	@echo "  make docker-down - Stop Docker services"
	@echo "  make migrate    - Run database migrations"

setup:
	@echo "Setting up development environment..."
	docker-compose up -d
	cd apps/api && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt
	cd apps/web && pnpm install

dev:
	@echo "Starting development servers..."
	@make docker-up
	@echo "Start backend: cd apps/api && uvicorn app.main:app --reload"
	@echo "Start frontend: cd apps/web && pnpm dev"

build:
	@echo "Building all packages..."
	pnpm build

test:
	@echo "Running tests..."
	cd apps/api && pytest
	cd apps/web && pnpm test

clean:
	@echo "Cleaning build artifacts..."
	rm -rf apps/web/.next
	rm -rf apps/api/__pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

docker-up:
	docker-compose up -d
	@echo "Waiting for services..."
	@sleep 5
	@echo "Services started!"

docker-down:
	docker-compose down

migrate:
	cd apps/api && alembic upgrade head

logs:
	docker-compose logs -f

db-shell:
	docker exec -it actorhub-postgres psql -U postgres -d actorhub

redis-cli:
	docker exec -it actorhub-redis redis-cli
