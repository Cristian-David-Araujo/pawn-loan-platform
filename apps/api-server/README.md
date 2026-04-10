# Pawn Loan API Server

FastAPI backend for pawn and personal loan management.

## Run

Use repository root docker compose:

```bash
docker compose up --build api-server
```

## API Base

- Base path: `/api/v1`
- Docs: `/docs`
- ReDoc: `/redoc`
- Health: `/health`

## Environment

The API uses the repository root `.env` as source of truth.

Key variables:

- `APP_NAME`, `APP_ENV`
- `DATABASE_URL`
- `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
- `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_ROLE`
- `DB_INIT_ON_STARTUP`, `DB_SEED_ON_STARTUP`, `DB_SEED_FORCE`
- `AUTO_INTEREST_GENERATION_ENABLED`, `AUTO_INTEREST_GENERATION_INTERVAL_MINUTES`

## Interest Generation Behavior

The platform supports three complementary mechanisms:

1. Loan creation trigger:
	- When `POST /api/v1/loans` creates a loan, due interest periods are generated immediately if disbursement is in the past.
2. Periodic automatic scheduler:
	- Runs in-process on API startup when `AUTO_INTEREST_GENERATION_ENABLED=true`.
	- Runs every `AUTO_INTEREST_GENERATION_INTERVAL_MINUTES`.
3. Manual generation endpoint:
	- `POST /api/v1/interest/generate` with `as_of_date`.

Generation details:

- Monthly period anchor is based on each loan disbursement day.
- Existing periods are skipped to avoid duplicate charges.
- Generated rows are stored as `interest_charges` and audited.

## Local Development

```bash
cd apps/api-server
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
set -a; source ../../.env; set +a
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## Tests

```bash
cd apps/api-server
pytest
```
