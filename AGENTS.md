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

## Design Workflow (Penpot / OpenPencil redesign)
These rules apply only when designing or redesigning pages in Penpot / OpenPencil. They do not apply to backend, tooling, formatting, testing, or other non-design work.
- Keep the base theme unchanged (surfaces, accent, text colors, Inter, radii); the redesign changes layout and composition only.
- Design **one page at a time**. After finishing a page, stop and ask the user to verify it before starting the next page. Do not batch several pages in one step.
- Move on only after the user confirms the current page.

## Git & Commit Conventions
-Don't leave behind any evidence that an ai did it