# AniMatch — Project Context and Current Progress

Use this document as context when asking ChatGPT (web) to create a practical project plan. Treat the implemented features below as the repository's current state; treat the planned features as goals that still need investigation and implementation.

## Project overview

AniMatch is a web app for discovering anime and getting recommendations that explain why each title may fit. The intended experience combines a browsable anime catalog, recommendations based on similar titles and quiz answers, and eventually a personalized taste profile. The product direction is a responsive, dark interface with cover art and clear recommendation explanations.

The catalog is sourced from AniList and stored locally so normal browsing and recommendation requests can use the local database. Anime with mature content should be excluded by default, with the server enforcing the preference.

## Intended product scope

The original v1 brief describes these goals:

- Browse, search, filter, and view anime details.
- Take a mood and genre quiz and receive recommendations.
- Find anime similar to a selected title, with a visible explanation for each result.
- Create an account, manage preferences, save titles, and rate titles from 1 to 10.
- Build a taste profile from quiz answers, ratings, and optionally an imported MyAnimeList list.
- Eventually accept natural-language discovery requests and translate them into structured recommendations.
- Provide useful experiences for signed-in and signed-out visitors.

These are goals, not a claim that every feature is already present. The current codebase is strongest in catalog, quiz, recommendation, browse/detail, and authentication foundations.

## Technology and repository

- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query, Vitest, and React Testing Library.
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy async, Alembic, Pydantic, SQLite for local development, pytest.
- **Anime data:** AniList GraphQL catalog sync and local recommendation index.
- **Deployment setup:** Dockerfiles and Docker Compose are present; production deployment is not confirmed.
- Main folders: `frontend/src`, `frontend/tests`, `backend/app`, `backend/tests`, `backend/alembic`, and `docs`.

## Implemented in the current repository

### Backend

- FastAPI application with health, anime catalog, authentication, and recommendation endpoints.
- Anime catalog schema and Alembic migrations, including genres, tags, maturity flags, and franchise relationships.
- AniList catalog synchronization CLI and local catalog/index logic.
- Anime browse/search/filter metadata and anime detail API.
- Quiz questions and quiz-based recommendation endpoint. Quiz answers can be saved to a signed-in user's taste profile.
- Similar-anime and signed-in personalized recommendation endpoints, including recommendation reason fields and mature-content handling.
- Email/password registration and login, session cookies, CSRF protection, rate limiting, account settings, and optional Google OAuth.
- Backend tests exist for auth, anime endpoints, recommendations, catalog sync, and health.

### Frontend

- Landing page, quiz and results flow, catalog browse, anime detail, login, registration, and settings routes.
- Search/filter controls, pagination, anime cards/posters, score display, and recommendation cards.
- API client and query hooks, auth context, toast messages, and responsive styling foundations.
- Frontend tests exist for core components, browse, auth/detail, quiz, and API client behavior.

## Known gaps and planning work

Confirm these against the code before turning them into detailed tasks; they are not evidenced as completed in the current implementation:

- **Watchlist and ratings:** The user model has a taste-profile JSON field, but the inspected models do not show persisted per-title saved-list or 1–10 rating records/endpoints/UI.
- **MyAnimeList import:** The brief describes Jikan and XML import, but no import workflow was found in the current app routes/services.
- **Natural-language / Gemini layer:** The brief describes an LLM discovery feature, but no Gemini integration or provider implementation appears in the current dependencies or routes.
- **Personalized homepage:** A personalized recommendation API exists, but the current frontend routes do not show a distinct personalized home/dashboard flow.
- **Release readiness:** Docker setup exists, but a production host, deployment workflow, monitoring, backups, and production database configuration should be assessed.
- **Frontend polish:** `docs/frontend-backlog.md` lists a more compact browse filter bar, flatter tag chips, and moving detail-page controls into the left column.
- **Scope decisions:** Reconcile the original phase plan and design docs with the actual product priorities. The design doc contains an older “awaiting Phase 2” note, while later docs and code show substantial later-phase work.

## Current progress snapshot

The repository has a working full-stack foundation and substantial feature code. The primary user journey—browse the locally synced catalog, inspect an anime, take a quiz, and receive recommendations—is represented across the backend and frontend. Authentication and optional Google OAuth are also implemented. The next plan should first establish a reliable, evidence-based feature/status checklist, then prioritize unfinished v1 capabilities and hardening based on product value and dependencies.

There are existing automated tests in both projects. This snapshot is based on repository files and route/model inspection; it does not assert that tests currently pass or that the app has been deployed.

## Planning request prompt

You can ask ChatGPT to use this context with a prompt like:

> Based on the project context and current progress above, create a phased, practical plan for taking AniMatch from its current repository state to a polished v1. Start by identifying assumptions and gaps that should be verified in the code. Prioritize work by dependencies and user value. For each phase, list concrete deliverables, likely backend/frontend/data work, acceptance criteria, and key risks. Keep implemented features separate from proposed work, and avoid assuming that the planned MyAnimeList import or Gemini feature already exists. Include a short list of decisions I need to make before implementation.
