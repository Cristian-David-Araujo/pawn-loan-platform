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
- `APP_NAME`, `APP_ENV`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `VITE_API_BASE_URL`, `VITE_API_USERNAME`, `VITE_API_PASSWORD`
- `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
- `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_ROLE`
- `DB_INIT_ON_STARTUP`, `DB_SEED_ON_STARTUP`, `DB_SEED_FORCE`
- `AUTO_INTEREST_GENERATION_ENABLED`, `AUTO_INTEREST_GENERATION_INTERVAL_MINUTES`

#### Interest generation variables

- `AUTO_INTEREST_GENERATION_ENABLED=true|false`: enables/disables periodic automatic interest generation in the API process.
- `AUTO_INTEREST_GENERATION_INTERVAL_MINUTES=1440`: scheduler interval in minutes (default is daily).
- `DB_INIT_ON_STARTUP=true`: required so settings and tables are available on startup.

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

### GitFlow + Auto Release + Auto Deploy

This repository includes GitHub Actions workflows to automate release and deployment when changes reach `main`.

- Workflow: `.github/workflows/pr-gitflow-guard.yml`
- Workflow: `.github/workflows/release-tag-and-deploy.yml`
- Script: `.github/scripts/calculate_version.sh`

Rules for pull requests targeting `main`:

- Only `release/*`, `hotfix/*`, and `develop` source branches are allowed.

Automatic behavior after a PR to `main` is merged:

- Calculates next semantic version based on GitFlow branch:
	- `release/x.y.z` or `hotfix/x.y.z`: uses explicit version from branch name.
	- `release/*` without explicit version: bumps minor.
	- `hotfix/*` without explicit version: bumps patch.
	- `develop`: bumps minor.
- Creates and pushes a Git tag in format `vX.Y.Z`.
- Deploys latest `main` on DigitalOcean via SSH and runs:
	- `docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d`

Required GitHub repository secrets:

- `DO_HOST`: Droplet public IP or hostname.
- `DO_USER`: SSH user (for example `root`).
- `DO_SSH_KEY`: Private SSH key with access to the droplet.
- `DO_APP_DIR` (optional): Repository directory in droplet. Defaults to `/opt/pawn-loan-platform`.

For a full step-by-step DigitalOcean guide, see:

- `docs/deployment-digitalocean.md`
- `docs/ci-cd-digitalocean.md`

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
	- `/interest`
	- `/collateral-items`
	- `/payments`
	- `/reports`

### Interest charge generation

- Charges are generated automatically when creating a loan if its disbursement date is in the past and there are due periods.
- Charges are generated periodically by an in-process scheduler controlled by `AUTO_INTEREST_GENERATION_ENABLED` and `AUTO_INTEREST_GENERATION_INTERVAL_MINUTES`.
- Charges can still be generated manually through `POST /api/v1/interest/generate`.
- The generation cycle uses each loan disbursement day as the monthly anchor and avoids duplicate periods.

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
