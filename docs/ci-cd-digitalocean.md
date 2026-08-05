# CI/CD GitFlow + Auto Release + Auto Deploy (DigitalOcean)

This guide automates your release and deployment flow when changes reach `main`.

## 1. Goal

Automate:

- PR validation to `main` using GitFlow rules.
- Automatic SemVer version calculation.
- Automatic Git tag creation (`vX.Y.Z`).
- Automatic deployment to DigitalOcean when a PR is merged into `main`.

## 2. What Is Already Implemented

Key files:

- `.github/workflows/pr-gitflow-guard.yml`
- `.github/workflows/alembic-migration-guard.yml`
- `.github/workflows/release-tag-and-deploy.yml`
- `.github/scripts/calculate_version.sh`

Current behavior:

- PRs to `main` are allowed from `release/*`, `hotfix/*`, and `develop`.
- PRs to `main` and `develop` must include a migration in `apps/api-server/alembic/versions/` whenever schema-related files change.
- When a PR is merged into `main`, the pipeline:
  - calculates the version,
  - creates and pushes a tag,
  - deploys to DigitalOcean via SSH.

## 3. Prerequisites

On GitHub:

- Permissions to configure repository secrets.
- GitHub Actions enabled.

On DigitalOcean (droplet):

- Ubuntu/Debian with SSH access.
- Docker Engine + Docker Compose Plugin installed.
- Repository cloned on server (default: `/opt/pawn-loan-platform`).
- `.env.production` configured at the repository root on the server.

## 4. Required GitHub Secrets

Go to:

- Repository -> Settings -> Secrets and variables -> Actions -> New repository secret

Access to the droplet:

1. `DO_HOST`
- Droplet public IP or domain.

2. `DO_USER`
- SSH user (for example `root` or `deploy`).

3. `DO_SSH_KEY`
- Full private SSH key, including:
  - `-----BEGIN ...-----`
  - `-----END ...-----`

4. `DO_SSH_KEY_B64` (recommended)
- Base64-encoded private SSH key in a single line.
- This avoids newline formatting issues in secrets.

5. `DO_APP_DIR` (optional)
- Project path on the server.
- If not defined, `/opt/pawn-loan-platform` is used.

Application secrets — these three, and only these three, are the production values that cannot
live in the repository. Everything else is versioned in
[deploy/digitalocean/production.env](../deploy/digitalocean/production.env), and the deploy
renders `.env.production` from both halves:

6. `POSTGRES_PASSWORD`
- Database password. `DATABASE_URL` is composed from it at deploy time, so it is not duplicated.
- Keep it URL-safe (`openssl rand -hex 24`): it ends up inside a connection string.

7. `JWT_SECRET_KEY`
- Token signing key (`openssl rand -hex 48`). The API refuses to boot in production while this
  holds the published development default. Rotating it logs everyone out, which is expected.

8. `ADMIN_PASSWORD`
- Seeds the admin account on the **first** boot only. After that the live password is the one in
  the database, changed from the users screen, and this secret goes stale by design.

Notes:

- The workflow accepts either `DO_SSH_KEY_B64` (preferred) or `DO_SSH_KEY` (fallback).
- If both are present, `DO_SSH_KEY_B64` is used.
- There is no `VITE_API_BASE_URL` secret. The browser's API base URL is a *build* input (Vite
  inlines it), it is not sensitive, and it now lives in `production.env` as the relative
  `/api/v1` — Caddy serves the SPA and the API on one origin, so the image is not tied to a
  hostname and a domain change needs no rebuild.

## 4.1 How to Generate and Use SSH Keys for GitHub Actions

Use a dedicated key pair for CI/CD (do not reuse your personal key).

On your local machine:

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_actions_do
```

This creates:

- Private key: `~/.ssh/github_actions_do`
- Public key: `~/.ssh/github_actions_do.pub`

Set your GitHub secret values as follows:

- `DO_SSH_KEY_B64` (recommended): base64 of `~/.ssh/github_actions_do` in one line.
- `DO_SSH_KEY` (fallback): paste full content of `~/.ssh/github_actions_do` (private key).
- Public key (`.pub`): add this on the server in `~/.ssh/authorized_keys` for the deploy user.

Generate base64 secret value:

Linux:

```bash
base64 -w0 ~/.ssh/github_actions_do
```

macOS:

```bash
base64 ~/.ssh/github_actions_do | tr -d '\n'
```

Private key format must look like this:

```text
-----BEGIN OPENSSH PRIVATE KEY-----
...
-----END OPENSSH PRIVATE KEY-----
```

Public key format must look like this:

```text
ssh-ed25519 AAAA... comment
```

If a key is ever exposed, rotate it immediately (generate a new key pair and replace both sides).

## 5. Recommended Server Setup

## 5.1 Create a deployment user (recommended)

You can use `root`, but a dedicated user (`deploy`) with Docker permissions is safer.

## 5.2 Add the public key on the server

On the server:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
nano ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Paste the public key associated with `DO_SSH_KEY`.

Then validate SSH login from your local machine before using GitHub Actions:

```bash
ssh -i ~/.ssh/github_actions_do deploy@YOUR_DROPLET_IP
```

If this fails, do not continue until SSH works without password prompts.

## 5.3 Verify Docker

```bash
docker --version
docker compose version
```

## 5.4 Verify project path and environment

```bash
cd /opt/pawn-loan-platform
ls -la
```

Do not expect `.env.production` on a fresh droplet: the first deploy generates it. What must be
there is the checkout — `docker-compose.prod.yml`, `deploy/digitalocean/` and `.git`.

Validate repository and branch state:

```bash
cd /opt/pawn-loan-platform
git remote -v
git branch --show-current
git fetch --all --tags --prune
```

Expected:

- Remote points to your GitHub repo.
- `main` branch exists and can be checked out.
- Tags are fetched successfully.

Run a manual deploy test once to confirm production compose works before automation — the same
script CI runs, with the three secrets supplied by hand:

```bash
cd /opt/pawn-loan-platform
git checkout main && git reset --hard origin/main
POSTGRES_PASSWORD='...' JWT_SECRET_KEY='...' ADMIN_PASSWORD='...' \
  IMAGE_TAG=latest ./deploy/digitalocean/remote_deploy.sh
```

## 6. Branching and Versioning Rules

Allowed PR sources to `main`:

- `release/*`, `hotfix/*`, `develop`.

Version calculation rules:

- `release/x.y.z` or `hotfix/x.y.z`: uses explicit version from branch name.
- `release/*` without explicit version: bumps minor.
- `hotfix/*` without explicit version: bumps patch.
- `develop`: bumps minor.

Quick example:

- Last tag: `v1.5.2`
- Merge from `develop` into `main`
- New tag: `v1.6.0`

## 7. What Auto Deploy Executes

When a PR is merged into `main`, the workflow:

1. Fetches repository tags.
2. Calculates the next version.
3. Creates and pushes an annotated tag on the merge commit.
4. Type-checks the web client, then builds and pushes both images to GHCR, tagged with the
   release tag and `latest`. The web client is built against `VITE_API_BASE_URL` read from
   `production.env`.
5. Connects to the droplet through the shared
   [deploy-to-droplet action](../.github/actions/deploy-to-droplet/action.yml) and runs
   [remote_deploy.sh](../deploy/digitalocean/remote_deploy.sh) on the server:

```bash
cd "$DO_APP_DIR"   # or /opt/pawn-loan-platform
git fetch --all --tags --prune
git checkout main
git reset --hard origin/main          # the checkout is a copy of main, not a place to edit
./deploy/digitalocean/remote_deploy.sh   # renders .env.production, then pulls and rolls forward
```

Two things follow from that script being the only copy of the procedure:

- **Nothing is built on the droplet.** `docker compose pull` fetches the images the release job
  already built, then `up -d` swaps them in. A 1 GB droplet cannot compile the web client.
- **`.env.production` is generated on every deploy** from `production.env` plus the three
  secrets. Hand-editing it on the server is lost work; change the versioned file instead.

## 7.1 Manual Deploy and Rollback

[deploy-droplet.yml](../.github/workflows/deploy-droplet.yml) — Actions → **Deploy To Droplet
(manual)** → Run workflow → image tag. It builds and tags nothing: it deploys an image tag that
already exists in GHCR, through the same action and the same script as a release. Use it to

- bring a fresh droplet up before any new merge to `main`, or
- roll back — run it with the previous tag (`v0.31.1`) and the stack returns to that image.

A rollback deploys the old *image* with the current `main` compose file and config. If a release
also changed the compose file or `production.env`, revert those in a PR as well.

Deploys are serialized (`concurrency: droplet-deploy`), so a manual run and a release cannot
land on the droplet at the same time.

## 8. Implementation Checklist

1. Confirm Docker and Compose are installed on the droplet.
2. Confirm the project exists in `DO_APP_DIR`.
3. Confirm `DOMAIN` in `production.env` already resolves to the droplet.
4. Create the GitHub secrets: droplet access plus the three application secrets (§4).
5. Open a test PR to `main` (from `develop` or `release/*`).
6. Verify `PR GitFlow Guard` passes.
7. Merge the PR.
8. Verify `Release Tag And Deploy` completes in Actions.
9. Validate production:
   - Frontend
   - `/docs`
   - `/health`

## 8.1 Detailed End-to-End Procedure

Follow this sequence exactly the first time:

1. Prepare server access
- Confirm droplet accepts SSH.
- Confirm deploy user can run Docker commands.

2. Prepare repository on server
- Clone repo into `/opt/pawn-loan-platform` (or your custom path).
- Nothing else: the first deploy generates `.env.production`.

3. Create CI/CD SSH key pair
- Generate dedicated key pair.
- Put public key in deploy user `authorized_keys`.
- Store private key in `DO_SSH_KEY_B64` (recommended) or `DO_SSH_KEY`.

4. Configure GitHub secrets
- Add `DO_HOST`, `DO_USER`, `DO_SSH_KEY_B64` (or `DO_SSH_KEY`), and optional `DO_APP_DIR`.
- Double-check there are no leading/trailing spaces.

5. Validate workflows exist on default branch
- Ensure these files are in the branch where Actions reads workflows:
  - `.github/workflows/pr-gitflow-guard.yml`
  - `.github/workflows/release-tag-and-deploy.yml`

6. Create a controlled test PR
- Source branch: `develop`.
- Target branch: `main`.
- Add a small harmless change (for example, docs).

7. Confirm pre-merge checks
- Verify `PR GitFlow Guard` is green.
- Resolve any failing checks before merge.

8. Merge PR and monitor release workflow
- Open Actions tab.
- Watch `Release Tag And Deploy` job.
- Confirm steps:
  - version calculated,
  - tag created/pushed,
  - SSH deploy executed successfully.

9. Validate deployment health
- Open domain root, `/docs`, and `/health`.
- Validate containers are healthy on server.

10. Confirm tag correctness
- Verify new `vX.Y.Z` exists in GitHub Releases/Tags.
- Check tag commit matches PR merge commit.

11. Capture baseline evidence
- Save workflow run URL.
- Save server compose status output.
- Keep this as known-good reference for future deploys.

## 8.2 Branch Protection Setup (Recommended)

In GitHub branch protection for `main`:

1. Require a pull request before merging.
2. Require status checks to pass before merging.
3. Select at least:
- `validate-gitflow-main-pr`
4. Restrict who can push directly to `main`.

This ensures deploys only happen through controlled PR merges.

## 9. Post-Deploy Validation

On the server:

```bash
cd /opt/pawn-loan-platform
docker compose --env-file .env.production -f docker-compose.prod.yml ps
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f --tail=200
```

In browser:

- `https://YOUR_DOMAIN`
- `https://YOUR_DOMAIN/docs`
- `https://YOUR_DOMAIN/health`

## 10. Troubleshooting

1. Error: Missing secret
- Verify exact secret names (`DO_HOST`, `DO_USER`, `DO_SSH_KEY_B64` or `DO_SSH_KEY`, `DO_APP_DIR`).

2. Error: SSH authentication failed
- Verify private key in GitHub and matching public key in `authorized_keys` for the correct user.
- Ensure the key is not passphrase-protected.
- If using `DO_SSH_KEY`, verify multiline formatting is preserved.
- Prefer `DO_SSH_KEY_B64` to avoid newline corruption.

3. Error: Empty APP_DIR or wrong path
- Set `DO_APP_DIR` or use default `/opt/pawn-loan-platform`.

4. Error: Tag already exists
- If it points to the same merge commit, the workflow continues.
- If it points to another commit, review your versioning strategy and existing tags.

5. Error in `docker compose up -d`
- Check the generated `.env.production` (`sudo cat .env.production`) against `production.env`.
- Check logs for `api-server`, `web-client`, `reverse-proxy`, `postgres`.
- `reverse-proxy` alone unhealthy or serving no certificate is almost always DNS: `DOMAIN` must
  resolve to this droplet, and port 80 must be reachable, before Let's Encrypt will issue.

6. Error: Permission denied while running Docker
- Add deploy user to docker group and re-login:

```bash
sudo usermod -aG docker deploy
```

7. Error: Workflow not triggered on merge
- Confirm PR target branch is `main`.
- Confirm merge actually happened (not just closed PR).
- Confirm workflow files exist in default branch and are not disabled.

8. Error: Could not resolve merge commit SHA
- Check PR merge strategy and ensure merge commit metadata is available.
- Retry with a standard merge commit if your policy allows it.

9. Error: Wrong repository path on server
- Set `DO_APP_DIR` explicitly in secrets.
- Verify the path contains `.git`, `docker-compose.prod.yml`, and `deploy/digitalocean/`.

## 11. Quick Manual Rollback

Run the **Deploy To Droplet (manual)** workflow with the previous tag (§7.1) — it deploys that
published image through the same path a release takes. On the droplet directly:

```bash
cd /opt/pawn-loan-platform
POSTGRES_PASSWORD='...' JWT_SECRET_KEY='...' ADMIN_PASSWORD='...' \
  IMAGE_TAG=vX.Y.Z ./deploy/digitalocean/remote_deploy.sh
```

Do not `git checkout vX.Y.Z` on the droplet to roll back: the images are tagged, so the tag goes
in `IMAGE_TAG` and the checkout stays on `main`. A detached checkout there makes the next
automatic deploy fail on branch state, and it does not roll back the running containers anyway.

Note that a rollback does **not** undo an Alembic migration the newer release applied. Restore the
database from a dump if a migration is what broke the release.

Then define a recovery strategy for `main` (revert or hotfix) and return to normal flow.

## 12. Recommended Best Practices

- Protect `main` with branch protection rules.
- Require successful status checks before merge.
- Use a `deploy` user instead of `root`.
- Rotate SSH keys periodically.
- Back up the database before sensitive changes.

## 13. Useful Commands

Show latest tags:

```bash
git tag --list 'v*' | sort -V | tail -n 10
```

Monitor containers:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

Service logs:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f api-server
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f web-client
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f reverse-proxy
```
