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
- `.github/workflows/release-tag-and-deploy.yml`
- `.github/scripts/calculate_version.sh`

Current behavior:

- PRs to `main` are allowed from `release/*`, `hotfix/*`, and `develop`.
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

Create:

1. `DO_HOST`
- Droplet public IP or domain.

2. `DO_USER`
- SSH user (for example `root` or `deploy`).

3. `DO_SSH_KEY`
- Full private SSH key, including:
  - `-----BEGIN ...-----`
  - `-----END ...-----`

4. `DO_APP_DIR` (optional)
- Project path on the server.
- If not defined, `/opt/pawn-loan-platform` is used.

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

- `DO_SSH_KEY`: paste the full content of `~/.ssh/github_actions_do` (private key).
- Public key (`.pub`): add this on the server in `~/.ssh/authorized_keys` for the deploy user.

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
ls -la .env.production
```

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

Run a manual deploy test once to confirm production compose works before automation:

```bash
cd /opt/pawn-loan-platform
git checkout main
git pull origin main
docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d
docker compose --env-file .env.production -f docker-compose.prod.yml ps
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
4. Connects to the droplet through SSH.
5. Runs on the server:

```bash
cd "$DO_APP_DIR"   # or /opt/pawn-loan-platform
git fetch --all --tags --prune
git checkout main
git pull origin main
docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d
```

## 8. Implementation Checklist

1. Confirm Docker and Compose are installed on the droplet.
2. Confirm the project exists in `DO_APP_DIR`.
3. Confirm `.env.production` exists and is valid.
4. Create the 4 GitHub secrets.
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
- Create and validate `.env.production`.

3. Create CI/CD SSH key pair
- Generate dedicated key pair.
- Put public key in deploy user `authorized_keys`.
- Store private key in `DO_SSH_KEY`.

4. Configure GitHub secrets
- Add `DO_HOST`, `DO_USER`, `DO_SSH_KEY`, and optional `DO_APP_DIR`.
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
- Verify exact secret names (`DO_HOST`, `DO_USER`, `DO_SSH_KEY`, `DO_APP_DIR`).

2. Error: SSH authentication failed
- Verify private key in GitHub and matching public key in `authorized_keys` for the correct user.

3. Error: Empty APP_DIR or wrong path
- Set `DO_APP_DIR` or use default `/opt/pawn-loan-platform`.

4. Error: Tag already exists
- If it points to the same merge commit, the workflow continues.
- If it points to another commit, review your versioning strategy and existing tags.

5. Error in `docker compose up --build -d`
- Check `.env.production`.
- Check logs for `api-server`, `web-client`, `reverse-proxy`, `postgres`.

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
- Verify the path contains `.git`, `docker-compose.prod.yml`, and `.env.production`.

## 11. Quick Manual Rollback

If you need to roll back to a previous tag:

```bash
cd /opt/pawn-loan-platform
git fetch --all --tags --prune
git checkout vX.Y.Z
docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d
```

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
