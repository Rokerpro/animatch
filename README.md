# animatch
An ai driven anime recommender website.

AniMatch is a hybrid anime recommendation platform featuring a sleek, minimal dark UI, mood/genre quiz, taste profiling from user ratings and MyAnimeList (MAL) imports, and a Google Gemini LLM layer translating natural-language queries into structured recommendations with transparent "Why this was recommended" explanations.

---

## 🛠 Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.x (async), Alembic, Pydantic v2, SQLite (dev) / PostgreSQL (prod).
- **Frontend**: React 18, TypeScript (strict), Vite, Tailwind CSS (WCAG AA compliant design tokens), React Router v6, TanStack Query v5.
- **Testing**: pytest + pytest-asyncio + httpx (backend); Vitest + React Testing Library (frontend).
- **Tooling**: ruff + black (Python); eslint + prettier (TypeScript/CSS); unified `Makefile`.
- **Infrastructure**: Containerized with multi-stage Dockerfiles and `docker-compose.yml`.

---

## 📋 Prerequisites

- **Python**: 3.11 or newer
- **Node.js**: v20 or newer (`npm` 10+)
- **Make**: Standard GNU make

---

## 🚀 Quickstart

### 1. Installation

Install all backend and frontend dependencies in a single step:

```bash
make install
```

This creates a Python virtual environment in `backend/.venv` and installs all npm packages in `frontend/node_modules`.

### 2. Environment Configuration

Copy the example environment configuration:

```bash
cp .env.example .env
```

Key environment variables:
- `DATABASE_URL`: SQLite async connection for development (`sqlite+aiosqlite:///./animatch.db`).
- `JWT_SECRET_KEY`: Secret key for signing session JWT cookies.
- `CORS_ORIGINS`: Allowed origins (defaults to `["http://localhost:5173"]`).
- `GEMINI_API_KEY`: Google Gemini API key (for LLM discovery layer).
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`: Optional Google OAuth credentials (mocked in tests).

### 3. Development Server

Start both the FastAPI backend (`http://localhost:8000`) and the Vite frontend dev server (`http://localhost:5173`) concurrently:

```bash
make dev
```

Alternatively, run each service individually:

```bash
# Backend only
make dev-backend

# Frontend only
make dev-frontend
```

---

## 🧪 Testing and Quality Control

Run automated test suites and linters across the entire stack:

```bash
# Run all backend and frontend tests (pytest + vitest)
make test

# Run all linters (ruff, black, eslint, prettier)
make lint

# Autoformat codebases across backend and frontend
make format
```

---

## 🐳 Docker Deployment

To build and run the containerized stack:

```bash
docker compose up --build
```

- Backend API: `http://localhost:8000/api/health`
- Frontend UI: `http://localhost:3000`

---

## 📁 Repository Structure

```text
├── backend/
│   ├── alembic/              # Alembic migration environment
│   ├── app/
│   │   ├── api/              # API routers and endpoints (/api/health)
│   │   ├── core/             # Pydantic settings and structured logging
│   │   ├── db/               # SQLAlchemy 2.x async engine and sessionmaker
│   │   └── main.py           # FastAPI app factory
│   ├── tests/                # pytest test suite
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/
│   ├── public/               # Static assets & favicon
│   ├── src/
│   │   ├── api/              # API fetchers (TanStack Query)
│   │   ├── components/       # UI components (Navbar, shell)
│   │   ├── pages/            # View pages (HomePage)
│   │   ├── App.tsx
│   │   ├── index.css         # Tailwind directives & design tokens
│   │   └── main.tsx
│   ├── tests/                # Vitest & React Testing Library tests
│   ├── Dockerfile
│   ├── package.json
│   ├── tailwind.config.js    # Design tokens & color system
│   └── vite.config.ts        # Vite dev proxy and alias config
├── docs/                     # Architecture & decision records
├── docker-compose.yml        # Multi-container orchestration
├── Makefile                  # Project automation control
├── PROJECT_BRIEF.md          # Full project brief & specification
└── README.md
```
