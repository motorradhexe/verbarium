# Project Structure

How the repository is laid out and where new code belongs. Nothing here is
feature code yet — this is the skeleton the roadmap in `REQUIREMENTS.md`
gets built into.

## Top level

```
verbarium/
├── backend/            FastAPI application (Python 3.11+)
├── frontend/           React application (Vite + TypeScript)
├── docs/               Design decisions and background
├── docker-compose.yml  Development stack: backend, frontend, optional PostgreSQL
├── .env.example        All environment variables, documented
├── REQUIREMENTS.md     Project context, decisions, roadmap
├── STRUCTURE.md        This file
└── LICENSE             MIT
```

## Backend

```
backend/
├── app/
│   ├── main.py           App factory, middleware, router registration
│   ├── api/
│   │   ├── router.py     Central router — feature routers register here
│   │   └── routes/       One module per resource
│   │       └── health.py GET /health
│   ├── core/
│   │   └── config.py     Settings from environment variables
│   ├── db/
│   │   └── session.py    Engine, session factory, declarative base
│   ├── models/           SQLAlchemy ORM models (empty)
│   ├── schemas/          Pydantic request/response schemas (empty)
│   └── services/         Business logic, import/export, AI providers (empty)
├── tests/                pytest suite, mirrors the app/ layout
├── Dockerfile
└── pyproject.toml        Dependencies and tooling config
```

**Where things go as the project grows**

| Concern | Location |
|---|---|
| New endpoint | `app/api/routes/<resource>.py`, registered in `app/api/router.py` |
| Database table | `app/models/<entity>.py` |
| Request/response shape | `app/schemas/<entity>.py` |
| Workflow, import/export, AI provider | `app/services/<topic>/` |
| Configuration, security helpers | `app/core/` |

Routes stay thin: validate input, call a service, return a schema. Business
logic lives in `services/` so it stays testable without HTTP, and reusable
for CLI or background jobs later.

**Routing convention.** `/health` sits at the root so orchestrators can probe
it without knowing the API layout. Everything else is mounted under
`VERBARIUM_API_PREFIX` (default `/api`). Interactive API docs: `/docs`.

## Frontend

```
frontend/
├── src/
│   ├── main.tsx    Entry point, mounts <App>
│   ├── App.tsx     Application shell (placeholder page)
│   └── index.css   Global styles
├── index.html
├── vite.config.ts  Dev server, /api and /health proxy to the backend
├── tsconfig*.json
├── Dockerfile
└── package.json
```

No UI framework, router, or state management is chosen yet — deliberately.
As the UI grows, the expected layout is `src/components/` (reusable
presentational pieces), `src/pages/` (route-level views), `src/api/` (backend
client), `src/i18n/` (DE/EN translations, per `REQUIREMENTS.md`).

The dev server proxies `/api` and `/health` to the backend, so frontend code
uses relative URLs and never needs to know the backend host.

## Configuration

All configuration comes from environment variables, documented in
`.env.example`. Backend variables use the `VERBARIUM_` prefix and are read by
`app/core/config.py`; the frontend reads `VITE_`-prefixed variables.

The database is selected with `VERBARIUM_DB_BACKEND` (`sqlite` or
`postgres`). `VERBARIUM_DATABASE_URL` overrides it entirely when a full
SQLAlchemy URL is needed. Application code only ever touches
`get_settings().sqlalchemy_url`, so no module needs to know which backend is
in use.

## Docker Compose

`docker compose up` starts `backend` and `frontend` against SQLite. PostgreSQL
lives behind the `postgres` profile, so it is only started when asked for:

```bash
docker compose up                       # SQLite
docker compose --profile postgres up    # PostgreSQL
```

Both services bind-mount their source directory and run in development mode
with hot reload. A production compose file (built frontend assets served by a
web server, no bind mounts) is a separate concern and comes later.
