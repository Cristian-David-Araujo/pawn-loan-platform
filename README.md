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
- `DATABASE_URL` (local runs)
- `DATABASE_URL_DOCKER` (container runs)
- `VITE_API_BASE_URL`, `VITE_API_USERNAME`, `VITE_API_PASSWORD`
- `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
- `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_ROLE`
- `DB_INIT_ON_STARTUP`, `DB_SEED_ON_STARTUP`, `DB_SEED_FORCE`
- `AUTO_INTEREST_GENERATION_ENABLED`, `AUTO_INTEREST_GENERATION_INTERVAL_MINUTES`
- `BACKUP_SCHEDULER_ENABLED`, `BACKUP_SCHEDULER_INTERVAL_MINUTES`, `BACKUP_LOCAL_DIRECTORY`

#### Interest generation variables

- `AUTO_INTEREST_GENERATION_ENABLED=true|false`: enables/disables periodic automatic interest generation in the API process.
- `AUTO_INTEREST_GENERATION_INTERVAL_MINUTES=1440`: scheduler interval in minutes (default is daily).
- `DB_INIT_ON_STARTUP=true`: required so settings and tables are available on startup.

#### Recurring backup variables

The schedule itself — frequency, hour, destination, retention, the Google Drive account — is
configured from **Settings → Automatic backups** and stored in the database. Only these three
are environment settings, and the schedule stays off until an administrator turns it on. See
[docs/scheduled-backups.md](docs/scheduled-backups.md).

- `BACKUP_SCHEDULER_ENABLED=true|false`: whether this deployment runs the backup thread at all.
- `BACKUP_SCHEDULER_INTERVAL_MINUTES=15`: how often the thread checks the clock, which is also the schedule's precision.
- `BACKUP_LOCAL_DIRECTORY=/var/backups/pawn-platform`: default folder for the local destination. In Docker it is the `backup_data` volume, so copies survive the container being recreated.

## Run with Docker (recommended)

From the repository root:

```bash
docker compose up --build -d
```

## Production Deployment

Production deployment files are included in this repository:

- `docker-compose.prod.yml`
- `deploy/digitalocean/production.env` — every non-secret production value, versioned
- `deploy/digitalocean/remote_deploy.sh` — renders `.env.production` and rolls the stack forward
- `deploy/digitalocean/Caddyfile`
- `apps/api-server/Dockerfile.prod`
- `apps/web-client/Dockerfile.prod`

`.env.production` is generated on the droplet by the deploy script from `production.env` plus
three GitHub secrets (`POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `ADMIN_PASSWORD`); it is not written
by hand and editing it on the server is overwritten by the next deploy. See
[docs/deployment-digitalocean.md](docs/deployment-digitalocean.md).

### GitFlow + Auto Release + Auto Deploy

This repository includes GitHub Actions workflows to automate release and deployment when changes reach `main`.

- Workflow: `.github/workflows/pr-gitflow-guard.yml`
- Workflow: `.github/workflows/alembic-migration-guard.yml`
- Workflow: `.github/workflows/release-tag-and-deploy.yml`
- Workflow: `.github/workflows/deploy-droplet.yml` — manual deploy / rollback to a published tag
- Action: `.github/actions/deploy-to-droplet/` — the single SSH deploy path, shared by both
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

Alembic migration guard behavior on PRs:

- If schema-related files change (currently `apps/api-server/src/infrastructure/persistence/models.py` or files under `apps/api-server/src/domain/enums/`), CI requires at least one new migration file in `apps/api-server/alembic/versions/`.
- If schema changed and no migration was added, the PR fails with instructions.
- Recommended fix command:
	- `cd apps/api-server && alembic revision --autogenerate -m "describe_change"`

Required GitHub repository secrets:

- `DO_HOST`: Droplet public IP or hostname.
- `DO_USER`: SSH user (for example `root`).
- `DO_SSH_KEY_B64` (preferred) or `DO_SSH_KEY`: Private SSH key with access to the droplet.
- `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `ADMIN_PASSWORD`: the only production values not
  versioned in `deploy/digitalocean/production.env`.

The deploy path is not a secret: it is the `app_dir` input of
`.github/actions/deploy-to-droplet`, defaulting to `/opt/pawn-loan-platform`.

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

Schema migrations are managed with Alembic.

Run latest migrations:

```bash
cd apps/api-server
alembic upgrade head
```

Create a new migration revision:

```bash
cd apps/api-server
alembic revision -m "describe_change"
```

Autogenerate revision from models:

```bash
cd apps/api-server
alembic revision --autogenerate -m "describe_change"
```

On API startup, initialization can be controlled with:

- `DB_INIT_ON_STARTUP=true`: run `alembic upgrade head` and ensure base admin/seed bootstrap flow is executed
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

## Local Development (DB in Docker, API and frontend local)

This is the recommended hybrid setup: PostgreSQL runs in Docker, while the API server and web client run locally.

### 1. Start the database

```bash
docker compose up -d postgres
```

### 2. API server

```bash
cd apps/api-server
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
set -a; source ../../.env; set +a
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

PowerShell equivalent:

```powershell
cd apps/api-server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Get-Content ..\..\.env | ForEach-Object {
	if ($_ -match '^(?!#)([^=]+)=(.*)$') {
		[Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
	}
}
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Notes:

- Use `DATABASE_URL` (with `localhost`) in `.env` for local API runs — not `DATABASE_URL_DOCKER`.
- `DATABASE_URL_DOCKER` is only used inside Docker containers.

### 3. Web client

```bash
cd apps/web-client
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

PowerShell equivalent:

```powershell
cd apps/web-client
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## Testing

Backend tests:

```bash
cd apps/api-server
pytest
```
