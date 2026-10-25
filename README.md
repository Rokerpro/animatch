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
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`: Optional Google OAuth credentials.

### Google OAuth Setup (Optional)
Email and password authentication works out of the box without Google credentials. To enable Google Sign-In:
1. Navigate to the [Google Cloud Console Credentials Page](https://console.cloud.google.com/apis/credentials).
2. Create an **OAuth 2.0 Client ID** with Application type **Web application**.
3. Under **Authorized redirect URIs**, add:
   - `http://localhost:8000/api/auth/google/callback` (for local development)
   - `https://your-production-domain.com/api/auth/google/callback` (for production)
4. Copy the generated Client ID and Client Secret into your `.env` file:
   ```env
   GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
   FRONTEND_URL=http://localhost:5173
   ```
5. If Google credentials are not set, endpoints return a clean 400 "not configured" response and automated tests mock the provider.

---

## 🔐 Accounts and Authentication (Phase 3)

The API provides secure session-based authentication:
- **Password Security**: Argon2 hashing (`argon2-cffi`), minimum 10 characters, rejection of common weak passwords, and constant-time dummy verification for non-existent users to defend against timing attacks.
- **Session Management**: Signed HS256 JWT stored in an `httpOnly`, `SameSite=Lax`, and `Secure` (in production) cookie (`access_token`).
- **CSRF Defense**: Double-submit cookie pattern (`csrf_token` cookie + `X-CSRF-Token` header) enforced on all state-changing endpoints (`POST`, `PATCH`, `DELETE`).
- **Rate Limiting**: Sliding-window rate limiter on login and registration tracking failed attempts per IP and per email with lockout and `Retry-After` backoff.
- **Account Linking**: Safe Google OAuth account linking requiring `email_verified == True` from Google.

### Auth Endpoints
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register with email + password (sets session & CSRF cookies) |
| `POST` | `/api/auth/login` | Login with email + password |
| `POST` | `/api/auth/logout` | Logout and clear session cookies (requires CSRF) |
| `GET` | `/api/auth/csrf` | Obtain / refresh CSRF token |
| `GET` | `/api/auth/me` | Fetch authenticated user profile |
| `PATCH` | `/api/auth/me` | Update `display_name` and `show_mature` preferences (requires CSRF) |
| `DELETE` | `/api/auth/me` | Delete account and all associated data (requires CSRF) |
| `GET` | `/api/auth/google/login` | Redirect to Google OAuth authorization |
| `GET` | `/api/auth/google/callback` | OAuth callback, safe verified linking & session issuance |

---


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
