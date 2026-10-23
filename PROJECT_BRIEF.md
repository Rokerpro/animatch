# AniMatch - Project Brief & Master Prompt

## Role
Senior full-stack engineer building AniMatch. Frontend decisions are clearly explained in code comments and end-of-phase summaries.

## Product
AniMatch is an anime recommendation website with a dark, sleek, minimal look. Recommendations come from a hybrid system that combines:
1. A title the user liked (similar-anime lookup).
2. A mood/genre quiz.
3. A taste profile built from the user's ratings, quiz answers, and an import of their MyAnimeList (MAL) list.

On top of that sits an LLM layer that accepts natural-language requests (for example: *something cozy like Frieren but shorter*) and turns them into structured filters plus a short explanation. Every recommendation must show a clear "Why this was recommended" explanation.

## Version 1 Scope
- **In Scope**: Accounts, watchlist/saved lists, rating titles 1-10, search with filters, "why recommended" explanations, taste-profile onboarding (quiz + MAL import), natural-language requests via LLM, personalized homepage for logged-in users, logged-out homepage.
- **Out of Scope (v1)**: Trailers, streaming links, seasonal page, social features, comments, collaborative filtering, admin panel, payments.

## Tech Stack
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.x, Alembic, SQLite for development (Postgres-compatible), Pydantic v2, httpx.
- **Frontend**: React + TypeScript (strict) + Vite, Tailwind CSS, React Router, TanStack Query.
- **Tests**: pytest + pytest-asyncio + httpx test client (backend); Vitest + React Testing Library (frontend).
- **Tooling**: ruff + black, eslint + prettier, Makefile with `install`, `dev`, `test`, `lint`, `format`.
- **Auth**: email+password (argon2 hashing) and Google OAuth (Authlib). Sessions use httpOnly, SameSite cookies carrying a signed JWT.
- **LLM**: Google Gemini via official `google-genai` SDK wrapped behind an `LLMProvider` interface. Key from `GEMINI_API_KEY`.
- **Hosting**: Cloud server (GitHub Education pack). Containerizable with Dockerfile + docker-compose.

## Data Sources
- **AniList GraphQL API**: Rate limit ~90 req/min. Paginate and cache everything locally so user-facing requests never hit AniList live.
- **Catalog Ingestion**: CLI seeding script (`python -m app.cli sync-catalog`) with a `--limit` flag (default 1,000 titles for local dev/test, up to 5,000 for prod). Resumable and idempotent.
- **MAL Import**: Fetch public list via Jikan API with polite rate limiting; parse uploaded MAL XML export. Map MAL IDs using AniList's `idMal` field.

## Mature Content Rule
Anime flagged `isAdult` or explicit adult tags is hidden everywhere by default (search, recommendations, LLM results, homepage). Logged-in users can toggle in settings; logged-out visitors get a toggle in `localStorage`. Enforced on the **server**, never only in the UI.

## Design Direction
Dark, sleek, minimal.
- Near-black background (`#09090b` / `#0B0B0F`).
- Single violet/indigo accent (`#8B7CF6`), WCAG AA compliant for text and buttons, defined as a Tailwind design token.
- Generous spacing, large cover art hero element, subtle motion (150-250ms), one clean sans-serif font, no clutter, no emoji in the UI.
- Responsive, mobile-first, keyboard accessible.

## Authentication & Credentials Handling
- Google OAuth: Mocked in automated tests. Email/password works out of the box with no Google credentials. If `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` are not set, the frontend hides the Google button and backend endpoints return a clean "not configured" response.

## Repository Layout
- `/backend` (`app/`, `tests/`, `alembic/`)
- `/frontend` (`src/`, `tests/`)
- `/docs`
- `docker-compose.yml`
- `Makefile`
- `README.md`
- `.env.example`
- `PROJECT_BRIEF.md`

## Phases
1. Scaffold and environment
2. Data layer
3. Auth
4. Recommendation engine
5. Frontend foundation and browse
6. Watchlist, ratings, taste profile
7. MAL import
8. LLM natural-language layer
9. Homepage and polish
10. Hardening and deployment
