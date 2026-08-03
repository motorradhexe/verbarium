# Verbarium

> Terminology Management for People Who Care About Words

Open-source, self-hosted terminology management for technical writers,
translators, and cross-functional teams. AI-ready, not FULL-AI: every feature
works without an AI provider, and AI enriches where you configure it with your
own API key.

**Status: project scaffolding.** No features are implemented yet. See
[`REQUIREMENTS.md`](REQUIREMENTS.md) for the full scope and roadmap, and
[`STRUCTURE.md`](STRUCTURE.md) for the repository layout.

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
uvicorn app.main:app --reload
pytest
```

**Frontend** (Node 20+):

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

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python / FastAPI |
| Frontend | React / Vite / TypeScript |
| Database | SQLite (default) or PostgreSQL |
| Deployment | Docker Compose |

## License

MIT — see [`LICENSE`](LICENSE).
