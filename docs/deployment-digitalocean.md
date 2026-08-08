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

## 5.1) Add Swap on a Small Droplet

Skip this on 4 GB or more. On a 1–2 GB droplet, add swap before deploying: PostgreSQL, two
uvicorn workers, nginx and Caddy fit, but with no headroom, and the kernel kills whichever
process asks for memory at the wrong moment — usually Postgres, mid-write.

```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
sysctl -w vm.swappiness=10 && echo 'vm.swappiness=10' >> /etc/sysctl.conf
```

Images are never built on the droplet (they are pulled pre-built from GHCR), which is what makes
a 1 GB box viable at all — `npm run build` on this hardware would be killed.

## 6) Clone Project and Configure Environment

```bash
cd /opt
git clone https://github.com/Cristian-David-Araujo/pawn-loan-platform.git
cd pawn-loan-platform
```

That is the whole configuration step: **`.env.production` is not written by hand.** It is
generated on every deploy by [remote_deploy.sh](../deploy/digitalocean/remote_deploy.sh) from
two sources, so what production runs is reviewable in a diff instead of living only in a file
someone edited over SSH:

| Source | Holds | Where to change it |
| --- | --- | --- |
| [deploy/digitalocean/production.env](../deploy/digitalocean/production.env) — versioned | every non-secret value: `DOMAIN`, `APP_ENV`, `POSTGRES_DB`/`USER`, admin username, bootstrap and interest-cycle flags, `VITE_API_BASE_URL` | edit the file, open a PR — it reaches production on the next deploy |
| GitHub Actions secrets | `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `ADMIN_PASSWORD` only | Settings → Secrets and variables → Actions |

`DATABASE_URL` is **composed** by the script from `POSTGRES_USER`, `POSTGRES_DB` and the
password secret, so the credentials exist in exactly one place — a second literal copy inside a
URL is how the two silently stop matching. Anything hand-edited into `.env.production` on the
droplet is overwritten by the next deploy; the repository is the source of truth.

Never put a secret in `production.env`: this repository is public.

Two values deserve attention:

- `JWT_SECRET_KEY` — the API refuses to start in production while this holds the published
  development default, and the deploy script refuses even earlier. Generate one with
  `openssl rand -hex 48`. Changing it later invalidates every open session, which is expected.
- `ADMIN_PASSWORD` is not the live credential. Once the account exists the password lives in the
  database and the operator changes it from the users screen, so this secret goes stale by
  design — editing it later changes nothing. If the admin is ever locked out, set
  `ADMIN_PASSWORD_RESET_ON_STARTUP=true` in `production.env` for one boot and turn it back off;
  it overwrites whatever password the operator had set.

`DOMAIN` must already resolve to the droplet before the deploy that uses it. Caddy asks
Let's Encrypt for a certificate for exactly that name, and issuance fails on a name that does not
point here yet — so create the A record first, then change `DOMAIN`. Behind Cloudflare, keep the
record on **DNS only** (grey cloud) at least until the certificate is issued: the orange cloud
terminates TLS itself and the HTTP-01 challenge has to reach Caddy.

## 7) Deploy the Stack

Normally you never run this: merging into `main` deploys (see
[ci-cd-digitalocean.md](ci-cd-digitalocean.md)). To bring a fresh droplet up by hand before the
first merge, run the same script CI runs, with the three secrets in the environment:

```bash
cd /opt/pawn-loan-platform
POSTGRES_PASSWORD='...' JWT_SECRET_KEY='...' ADMIN_PASSWORD='...' \
  IMAGE_TAG=latest ./deploy/digitalocean/remote_deploy.sh
```

It renders `.env.production` (mode 600), logs into GHCR if given a token, pulls the pre-built
images and starts the stack. There is deliberately no `--build`: the images come from the
release pipeline, so the droplet never compiles anything.

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

Access logs live on `reverse-proxy`. Caddy is the only component that sees every request with the
real client IP — nginx and the API are both behind it — so this is where to look first when a
browser reports a failure the application has no record of:

```bash
# every request, as JSON
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f reverse-proxy

# just the logins, with status
docker compose --env-file .env.production -f docker-compose.prod.yml logs reverse-proxy \
  | grep auth/login
```

An empty result there is itself the answer: the request never arrived, so the problem is DNS, the
client's cache, or the network — not the credentials. The API adds its own uvicorn access line per
request, and every service caps its log at 10 MB × 3 files (`x-logging` in the compose file);
Docker's json-file driver keeps no bound of its own.

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

Update to latest code — merge into `main` and let the pipeline do it, or run the
**Deploy To Droplet (manual)** workflow with an image tag. The equivalent by hand:

```bash
cd /opt/pawn-loan-platform
git fetch --all --tags --prune && git checkout main && git reset --hard origin/main
POSTGRES_PASSWORD='...' JWT_SECRET_KEY='...' ADMIN_PASSWORD='...' \
  IMAGE_TAG=latest ./deploy/digitalocean/remote_deploy.sh
```

`git reset --hard` rather than `git pull`: the droplet's checkout is a copy of `main`, not a place
to edit, and a stray local change there would otherwise block every deploy with a merge
conflict. Untracked files — including the generated `.env.production` — are left alone.

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
