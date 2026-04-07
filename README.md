# Pawn & Personal Loan Management Platform

Monorepo for a pawn-backed and personal loan platform with a FastAPI backend, Vue 3 frontend, and PostgreSQL database.

## Stack

- Backend: FastAPI + SQLAlchemy (Python 3.12)
- Frontend: Vue 3 + Vite + TypeScript
- Database: PostgreSQL 16
- Orchestration: Docker Compose

## Project Layout

```text
pawn-loan-platform/
├── apps/
│   ├── api-server/      # FastAPI backend
│   └── web-client/      # Vue application
├── docs/
├── docker-compose.yml
└── README.md
```

## Prerequisites

- Docker + Docker Compose plugin
- (Optional for local/non-Docker runs) Python 3.12 and Node.js 20+

## Environment Setup

Use a single global environment file at the repository root:

```bash
cp .env.example .env
```

The platform is configured to read shared runtime variables from root `.env` only.

### Important variables (root `.env`)

- `WEB_CLIENT_PORT`, `API_SERVER_PORT`, `POSTGRES_PORT`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `VITE_API_BASE_URL`, `VITE_API_USERNAME`, `VITE_API_PASSWORD`
- `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
- `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_ROLE`
- `DB_INIT_ON_STARTUP`, `DB_SEED_ON_STARTUP`, `DB_SEED_FORCE`

## Run with Docker (recommended)

From the repository root:

```bash
docker compose up --build -d
```

## Production Deployment

Production deployment files are included in this repository:

- `docker-compose.prod.yml`
- `.env.production.example`
- `deploy/digitalocean/Caddyfile`
- `apps/api-server/Dockerfile.prod`
- `apps/web-client/Dockerfile.prod`

For a full step-by-step DigitalOcean guide, see:

- `docs/deployment-digitalocean.md`

Stop services:

```bash
docker compose down
```

Start only selected services:

```bash
docker compose up --build api-server
docker compose up --build web-client
```

## Service URLs

- Frontend: `http://localhost:5173`
- API docs (Swagger): `http://localhost:8000/docs`
- API ReDoc: `http://localhost:8000/redoc`
- API health: `http://localhost:8000/health`

## Backend Notes

- API base path: `/api/v1`
- Main route groups:
	- `/auth`, `/users`
	- `/customers`
	- `/loan-applications`, `/loans`
	- `/collateral-items`
	- `/payments`
	- `/reports`

Default development admin credentials (unless overridden in env):

- Username: `admin`
- Password: `admin123`

Example login payload:

```json
{
	"username": "admin",
	"password": "admin123"
}
```

## Database Initialization & Seed

On API startup, initialization can be controlled with:

- `DB_INIT_ON_STARTUP=true`: create/update tables
- `DB_SEED_ON_STARTUP=true`: insert sample data
- `DB_SEED_FORCE=false`: do not reset sample data by default

Manual bootstrap inside the API container:

```bash
docker compose exec api-server python -m src.infrastructure.tasks.bootstrap_db --seed
```

Force reseed:

```bash
docker compose exec api-server python -m src.infrastructure.tasks.bootstrap_db --seed --force-seed
```

## Local Development (without Docker)

### API server

```bash
cd apps/api-server
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
set -a; source ../../.env; set +a
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Web client

```bash
cd apps/web-client
npm install
set -a; source ../../.env; set +a
npm run dev -- --host 0.0.0.0 --port 5173
```

## Testing

Backend tests:

```bash
cd apps/api-server
pytest
```
