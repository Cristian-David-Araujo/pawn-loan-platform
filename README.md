# Pawn and Personal Loan Management Platform

Monorepo scaffold for a pawn-backed and personal loan platform.

## Tech Stack

- Backend: FastAPI (Python)
- Frontend: Vue 3 + Vite + TypeScript
- Database: PostgreSQL
- Runtime: Docker + Docker Compose

## Repository Structure

```text
pawn-loan-platform/
├── apps/
│   ├── web-client/
│   └── api-server/
├── database/
├── infrastructure/
├── docs/
├── .github/
├── docker-compose.yml
└── README.md
```

## Docker Services

- `web-client`: Vue development server on port `5173`
- `api-server`: FastAPI development server on port `8000`
- `postgres`: PostgreSQL on port `5432`

## Environment Files

- Root source of truth: `.env`
- App-local files:
	- `apps/api-server/.env`
	- `apps/web-client/.env`

Versioned templates:

- `.env.example`
- `apps/api-server/.env.example`
- `apps/web-client/.env.example`

`docker-compose.yml` is configured to reference the root `.env` so shared settings are centralized.

Create local env files from templates:

```bash
cp .env.example .env
cp apps/api-server/.env.example apps/api-server/.env
cp apps/web-client/.env.example apps/web-client/.env
```

## Run with Docker Compose

From the repository root:

```bash
docker compose up --build
```

Run only frontend prototype (no backend dependency required for UI navigation):

```bash
docker compose up --build web-client
```

Run or rebuild only backend service:

```bash
docker compose up --build api-server
```

To stop:

```bash
docker compose down
```

## Notes

- `web-client` expects `apps/web-client/package.json`.
- `api-server` expects `apps/api-server/pyproject.toml` or `apps/api-server/requirements.txt`.
- Shared Docker settings (ports, DB credentials, API URL) are read from `.env`.
- `.gitignore` is configured to avoid committing secrets. Only `.env.example` files should be committed.
- If those files are still missing, containers stay running in idle mode to keep the scaffold ready.
- Current frontend prototype uses local mock state and does not require backend APIs.

## Backend Quick Start

- FastAPI docs: `http://localhost:8000/docs`
- Health endpoint: `http://localhost:8000/health`
- Default bootstrap admin (if not overridden by env):
	- Username: `admin`
	- Password: `admin123`

Example login payload:

```json
{
	"username": "admin",
	"password": "admin123"
}
```

Important API groups currently implemented:

- Authentication: `/api/v1/auth/*`, `/api/v1/users`
- Customers: `/api/v1/customers`
- Loans and applications: `/api/v1/loan-applications`, `/api/v1/loans`
- Collateral: `/api/v1/collateral-items`
- Payments: `/api/v1/payments`
- Finance: `/api/v1/interest/generate`, `/api/v1/loans/{id}/balance`, `/api/v1/loans/{id}/ledger`
- Reporting: `/api/v1/reports/*`

## Database Init and Seed (Development Best Practice)

The backend uses an idempotent startup bootstrap:

- Creates tables from SQLAlchemy metadata.
- Ensures admin user exists.
- Seeds demo data only when enabled.

Environment flags:

- `DB_INIT_ON_STARTUP=true`
- `DB_SEED_ON_STARTUP=true`
- `DB_SEED_FORCE=false`

Manual bootstrap command inside container:

```bash
docker compose exec api-server python -m src.infrastructure.tasks.bootstrap_db --seed
```

Force reseed (clears sample business data and recreates it):

```bash
docker compose exec api-server python -m src.infrastructure.tasks.bootstrap_db --seed --force-seed
```
