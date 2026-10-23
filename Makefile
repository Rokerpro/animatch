SHELL := /bin/bash
.PHONY: help install dev dev-backend dev-frontend test test-backend test-frontend lint lint-backend lint-frontend format format-backend format-frontend build clean

PYTHON := backend/.venv/bin/python
PIP := backend/.venv/bin/pip
PYTEST := backend/.venv/bin/pytest
RUFF := backend/.venv/bin/ruff
BLACK := backend/.venv/bin/black

help:
	@echo "AniMatch Project Control"
	@echo "  make install         Install backend and frontend dependencies"
	@echo "  make dev             Run backend and frontend servers concurrently"
	@echo "  make test            Run all backend and frontend automated tests"
	@echo "  make lint            Run linters and formatting checks across full stack"
	@echo "  make format          Automatically format all backend and frontend code"
	@echo "  make build           Build production containers or frontend assets"

install:
	@echo "==> Setting up backend virtual environment and dependencies..."
	@python3 -m venv backend/.venv
	@$(PIP) install --upgrade pip
	@$(PIP) install -r backend/requirements.txt
	@echo "==> Setting up frontend dependencies..."
	@cd frontend && npm install

dev:
	@echo "==> Starting AniMatch full stack in development mode..."
	@trap 'kill 0' SIGINT SIGTERM EXIT; \
		(cd backend && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000) & \
		(cd frontend && npm run dev) & \
		wait

dev-backend:
	@cd backend && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	@cd frontend && npm run dev

test: test-backend test-frontend

test-backend:
	@echo "==> Running backend pytest suite..."
	@cd backend && .venv/bin/pytest -v

test-frontend:
	@echo "==> Running frontend Vitest suite..."
	@cd frontend && npm test

lint: lint-backend lint-frontend

lint-backend:
	@echo "==> Checking backend with ruff and black..."
	@cd backend && .venv/bin/ruff check .
	@cd backend && .venv/bin/black --check .

lint-frontend:
	@echo "==> Checking frontend with eslint and prettier..."
	@cd frontend && npm run lint
	@cd frontend && npm run format:check

format: format-backend format-frontend

format-backend:
	@echo "==> Formatting backend code..."
	@cd backend && .venv/bin/ruff check --fix .
	@cd backend && .venv/bin/black .

format-frontend:
	@echo "==> Formatting frontend code..."
	@cd frontend && npm run format
	@cd frontend && npm run lint:fix

build:
	@echo "==> Building frontend bundle..."
	@cd frontend && npm run build
