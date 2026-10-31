# AniMatch Development Instructions

## Build & Development Commands
- **Install dependencies**: `make install`
- **Run dev servers (concurrent backend + frontend)**: `make dev`
- **Run backend server**: `make dev-backend` (port 8000)
- **Run frontend Vite dev server**: `make dev-frontend`
- **Run all tests**: `make test` (backend pytest + frontend vitest)
- **Run backend tests**: `make test-backend` (`cd backend && .venv/bin/pytest -v`)
- **Run frontend tests**: `make test-frontend` (`cd frontend && npm test`)
- **Lint code**: `make lint` (ruff + black for backend, eslint + prettier for frontend)
- **Format code**: `make format` (ruff --fix + black for backend, prettier + eslint fix for frontend)
- **Build frontend**: `make build`

## Architecture & Tech Stack
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.x, Alembic, SQLite/PostgreSQL, Pydantic v2.
- **Frontend**: React, TypeScript (strict), Vite, Tailwind CSS, TanStack Query, React Router.
- **LLM / AI**: Google Gemini via `google-genai` SDK behind `LLMProvider` interface (`GEMINI_API_KEY`).
- **External APIs**: AniList GraphQL API, Jikan API (MAL import).

## Key Coding Guidelines & Rules
- **Mature Content Rule**: Anime flagged `isAdult` or explicit adult tags must be hidden everywhere by default. Enforced on the **server**, never only in the UI.
- **Design Direction**: Dark, sleek, minimal (`#09090b` background, `#8B7CF6` violet/indigo accent). No emojis in UI.
- **Code Style**:
  - Python: Ruff and Black formatting, strict type hints.
  - TypeScript: Strict mode, clean components, Tailwind CSS tokens.
- **Testing**: Write tests for new features and bug fixes across backend (pytest) and frontend (Vitest / React Testing Library).

## Git & Commit Conventions
- End git commit messages with:
  `Co-Authored-By: Claude Code <noreply@anthropic.com>`
- End pull request descriptions with:
  `🤖 Generated with [Claude Code](https://claude.com/claude-code)`
