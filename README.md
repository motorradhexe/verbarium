# Verbarium

[![CI](https://github.com/motorradhexe/verbarium/actions/workflows/ci.yml/badge.svg)](https://github.com/motorradhexe/verbarium/actions/workflows/ci.yml)

> Terminology Management for People Who Care About Words

Open-source, self-hosted terminology management for technical writers,
translators, and cross-functional teams. AI-ready, not FULL-AI: every feature
works without an AI provider, and AI enriches where you configure it with your
own API key.

**Status: early development.** Data model, migrations, authentication, and the
first-run setup wizard are in place. Terminology features are next. See
[`REQUIREMENTS.md`](REQUIREMENTS.md)
for the full scope and roadmap, [`STRUCTURE.md`](STRUCTURE.md) for the
repository layout, and [`docs/DATA-MODEL-DECISIONS.md`](docs/DATA-MODEL-DECISIONS.md)
for why the model looks the way it does.

## Quick start

```bash
cp .env.example .env       # optional — defaults work out of the box
docker compose up
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend | http://localhost:8000 |
| Health check | http://localhost:8000/health |
| API docs | http://localhost:8000/docs |

Both services run with hot reload and bind-mount their source directory, so
edits are picked up without a rebuild.

### First run

A fresh instance has no accounts. Create the workspace and the first Admin
through the setup wizard, which closes itself once an account exists:

```bash
curl -X POST http://localhost:8000/api/setup \
  -H 'Content-Type: application/json' \
  -d '{
    "workspace_name": "Coffee Terminology",
    "languages": [{"code": "de"}, {"code": "en"}],
    "admin_email": "you@example.org",
    "admin_display_name": "Your Name",
    "admin_password": "a-long-passphrase-you-remember"
  }'
```

Then sign in at `POST /api/auth/login`; the session arrives as an HTTP-only
cookie. Further accounts are created by an Admin at `POST /api/users` — there
is no self-registration.

### With PostgreSQL

SQLite is the default. For team deployments, start the PostgreSQL profile and
switch the backend over:

```bash
# in .env
VERBARIUM_DB_BACKEND=postgres

docker compose --profile postgres up
```

## Running without Docker

**Backend** (Python 3.11+):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
pytest
```

**Frontend** (Node 22.12+):

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` and `/health` to `http://localhost:8000`;
override with `VITE_API_PROXY_TARGET`.

## Configuration

All settings come from environment variables and are documented in
[`.env.example`](.env.example). Backend variables use the `VERBARIUM_` prefix.

## Troubleshooting

**Frontend dependencies changed.** `node_modules` lives in an anonymous volume
so the bind-mounted host directory cannot shadow it. After changing
`package.json`, refresh it explicitly:

```bash
docker compose up --build --renew-anon-volumes frontend
```

**Start from a clean database.** `docker compose down -v` removes the SQLite
and PostgreSQL volumes along with the containers.

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python / FastAPI |
| Frontend | React / Vite / TypeScript |
| Database | SQLite (default) or PostgreSQL |
| Deployment | Docker Compose |

## License

MIT — see [`LICENSE`](LICENSE).
