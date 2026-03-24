# Pawn Loan Platform

Microservices-ready monorepo for pawn-backed and personal loan management.

## Quick Start (Local)

1. Copy env file:

```bash
cp .env.example .env
```

2. Start infrastructure and services:

```bash
docker compose -f ops/docker/compose/docker-compose.local.yml --env-file .env up -d --build
```

3. Stop everything:

```bash
docker compose -f ops/docker/compose/docker-compose.local.yml --env-file .env down
```

## Repository Layout

- `apps/`: runnable applications (frontend, gateway, services)
- `packages/`: shared libraries and contracts
- `ops/`: Docker, deployment, and operations assets
- `database/`: local init scripts, seeds, backups
- `docs/`: architecture and business documentation

## Notes

- This scaffold intentionally starts simple.
- Service business logic can be added incrementally per module.
