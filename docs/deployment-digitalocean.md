# DigitalOcean Deployment Guide (Production)

This guide deploys the full platform (web, API, PostgreSQL) on a single DigitalOcean Droplet with Docker Compose and automatic HTTPS using Caddy.

## 1) Prerequisites

- A DigitalOcean account.
- A domain name managed in your DNS provider.
- SSH key configured in DigitalOcean.
- Local tools: `git`, `ssh`, and terminal access.

## 2) Create the Droplet

Recommended baseline:

- Image: Ubuntu 24.04 LTS
- Plan: Basic / Shared CPU (at least 2 vCPU, 4 GB RAM)
- Storage: 80 GB or more
- Authentication: SSH keys only (recommended)

Enable backups in DigitalOcean for safer recovery.

## 3) Point Domain to the Droplet

1. Copy the droplet public IPv4.
2. Create an `A` record for your app domain (for example `app.example.com`) pointing to that IP.
3. Wait for DNS propagation.

## 4) Open Firewall Rules

Allow inbound:

- `22/tcp` (SSH)
- `80/tcp` (HTTP)
- `443/tcp` (HTTPS)

Block all other inbound ports.

## 5) Install Docker on the Droplet

SSH into the server:

```bash
ssh root@YOUR_DROPLET_IP
```

Install Docker Engine + Compose plugin:

```bash
apt update && apt upgrade -y
apt install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable docker
systemctl start docker
```

## 6) Clone Project and Configure Environment

```bash
cd /opt
git clone https://github.com/Cristian-David-Araujo/pawn-loan-platform.git
cd pawn-loan-platform
cp .env.production.example .env.production
```

Edit `.env.production` and set secure values:

- `DOMAIN` (for example `app.example.com`)
- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `JWT_SECRET_KEY` — **required**: the API refuses to start in production while this holds the
  published development default. Generate one with `openssl rand -base64 48`.
- `ADMIN_PASSWORD` — only seeds the admin account on the very first boot
- `VITE_API_BASE_URL` (for example `https://app.example.com/api/v1`)

Important: `DATABASE_URL` credentials must match `POSTGRES_USER` and `POSTGRES_PASSWORD`.

`ADMIN_PASSWORD` is not the live credential. Once the account exists, the password lives in the
database and the operator changes it from the users screen, so this variable goes stale by
design — editing it later changes nothing. If the admin is ever locked out, set
`ADMIN_PASSWORD_RESET_ON_STARTUP=true` for one boot and turn it back off; be aware that this
overwrites whatever password the operator had set.

## 7) Deploy the Stack

From repository root:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d
```

Production compose includes a one-shot `db-bootstrap` service that initializes schema/admin data before the API starts. The API also keeps `DB_INIT_ON_STARTUP=true` as a safe fallback, so deployments remain automatic without manual DB bootstrap commands.

Schema changes are managed with Alembic migrations. During startup/bootstrap, the platform runs `alembic upgrade head`, so new releases apply pending revisions automatically.

Check status:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

Tail logs:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f
```

If API appears unhealthy, check bootstrap logs first:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs db-bootstrap
```

Verify applied migration version:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml exec api-server \
  alembic current
```

List migration history:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml exec api-server \
  alembic history
```

## 8) Verify Deployment

- Web app: `https://YOUR_DOMAIN`
- API docs: `https://YOUR_DOMAIN/docs`
- Health endpoint: `https://YOUR_DOMAIN/health`

If HTTPS certificate issuance fails, verify DNS and that ports `80` and `443` are publicly reachable.

## 9) Operational Commands

Restart services:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml restart
```

Stop services:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml down
```

Full teardown (remove containers, network, and volumes):

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml down --volumes --remove-orphans
```

Optional: also remove images built by this compose project:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml down --volumes --remove-orphans --rmi local
```

Optional: remove unused Docker resources system-wide (use with caution):

```bash
docker system prune -af --volumes
```

Update to latest code:

```bash
cd /opt/pawn-loan-platform
git pull
docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d
```

## 10) Backup and Restore (PostgreSQL)

Create backup:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > /opt/pawn_loan_backup.sql
```

Restore backup:

```bash
cat /opt/pawn_loan_backup.sql | docker compose --env-file .env.production -f docker-compose.prod.yml exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

## 11) Security Recommendations

- Use long random secrets for `POSTGRES_PASSWORD` and `JWT_SECRET_KEY`. Use a strong
  `ADMIN_PASSWORD` too, but remember it only applies to the first boot — the password that
  actually guards the account is the one stored in the database, changed from the users screen.
- Keep system packages updated (`apt update && apt upgrade -y`).
- Restrict SSH (disable password login, optionally change port).
- Use DigitalOcean backups and snapshots.
- Consider managed PostgreSQL for higher availability.
