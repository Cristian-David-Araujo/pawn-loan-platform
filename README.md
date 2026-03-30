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
