.PHONY: up down build restart logs test clean help

# Default
help:
	@echo "Pawn Loan Platform - Available commands:"
	@echo ""
	@echo "  make up        - Start all services"
	@echo "  make down      - Stop all services"
	@echo "  make build     - Build all Docker images"
	@echo "  make restart   - Restart all services"
	@echo "  make logs      - Tail logs from all services"
	@echo "  make test      - Run all backend tests"
	@echo "  make clean     - Remove containers, volumes, and images"
	@echo "  make migrate   - Run Alembic migrations for all services"
	@echo "  make seed      - Seed initial data"
	@echo ""

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

restart:
	docker compose restart

logs:
	docker compose logs -f

clean:
	docker compose down -v --rmi all

test-identity:
	cd backend/identity-service && pip install -r requirements.txt -q && python -m pytest tests/ -v

test-customer:
	cd backend/customer-service && pip install -r requirements.txt -q && python -m pytest tests/ -v

test-loan:
	cd backend/loan-service && pip install -r requirements.txt -q && python -m pytest tests/ -v

test-collateral:
	cd backend/collateral-service && pip install -r requirements.txt -q && python -m pytest tests/ -v

test-finance:
	cd backend/finance-service && pip install -r requirements.txt -q && python -m pytest tests/ -v

test-payment:
	cd backend/payment-service && pip install -r requirements.txt -q && python -m pytest tests/ -v

test:
	@echo "Running all backend service tests..."
	$(MAKE) test-identity
	$(MAKE) test-customer
	$(MAKE) test-loan
	$(MAKE) test-collateral
	$(MAKE) test-finance
	$(MAKE) test-payment
	@echo "All tests complete."

migrate:
	@echo "Running Alembic migrations..."
	cd backend/identity-service && alembic upgrade head
	cd backend/customer-service && alembic upgrade head
	cd backend/loan-service && alembic upgrade head
	cd backend/collateral-service && alembic upgrade head
	cd backend/finance-service && alembic upgrade head
	cd backend/payment-service && alembic upgrade head

shell-identity:
	docker compose exec identity-service /bin/sh

shell-customer:
	docker compose exec customer-service /bin/sh

shell-loan:
	docker compose exec loan-service /bin/sh

ps:
	docker compose ps
