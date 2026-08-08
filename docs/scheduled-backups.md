# Recurring backups

The manual export (`GET /backup/export`, the **Download export** button) only produces a copy
while somebody remembers to press it. This is the same archive, taken on a schedule and stored
somewhere the server is not.

Everything an operator can change lives in the database and is edited from **Settings →
Automatic backups**: whether it runs, how often, at what hour, where the copy goes, and how
many copies to keep. The environment carries only deployment facts.

## How it works

- A daemon thread per uvicorn worker (`BackupScheduler`) wakes every
  `BACKUP_SCHEDULER_INTERVAL_MINUTES` and asks the database whether the current slot still
  needs a copy. That interval is therefore the schedule's precision: "2am" means "within
  fifteen minutes of 2am" by default.
- Slots are computed in `GlobalSettings.timezone`, because "every day at 2am" is a statement
  about the business's clock.
- The answer to "is a copy still needed" comes from `backup_runs`, not from anything a worker
  remembers. A restart, a redeploy, or three days of downtime therefore cannot skip a slot: the
  copy is taken as soon as the server is back, and taken **once**.
- Only one worker actually runs it — `pg_try_advisory_lock(9021003)`, its own lock id, distinct
  from the interest cycle's. A backup is a read and has no reason to be delayed by a billing
  run.
- Every attempt writes a `BackupRun` row, successful or not, with the error in full. That table
  is the only way to tell a working schedule from one that stopped in June: from the outside
  both look like nothing happening.
- A slot that fails is retried up to `MAX_ATTEMPTS_PER_SLOT` (3) times and then left alone
  until the next one. Without the cap a revoked Drive token writes a row every fifteen minutes
  and buries the first failure, which is the row that says what broke.
- A **manual** run ("Back up now") never satisfies the schedule. It is an extra copy; counting
  it would let a manual run at 1am silently cancel the 2am one.

## Destinations

**Folder on the server** (`local_directory`) — written to `BACKUP_LOCAL_DIRECTORY`, mounted as
the `backup_data` Docker volume so the copies survive the container being recreated. A copy
here protects against a bad release, **not** against losing the droplet.

**Google Drive** (`google_drive`) — the copy that survives losing the server.

Copies beyond **Copies to keep** are removed from the destination, oldest first, using the
timestamp in the archive's own filename. Only files matching the export naming pattern are ever
deleted: the destination folder is the operator's folder and may hold anything else.

## Setting up Google Drive

The app authorises **your own Google account** over OAuth 2.0 and uploads into a folder it
creates. Files land in that account's Drive on its own quota — 15 GB on a free account, against
archives of kilobytes to a few megabytes.

A **service account** is deliberately not offered. Google removed the storage quota of service
accounts in 2021: the service account becomes the owner of whatever it uploads, so the bytes are
charged to a quota of zero and the upload fails with `storageQuotaExceeded` even inside a folder
shared with it. It only works against a Shared Drive, which is a paid Workspace feature.

### Steps

1. In [Google Cloud Console](https://console.cloud.google.com), create a project.
2. **APIs & Services → Library**: enable the **Google Drive API**.
3. **APIs & Services → OAuth consent screen**: configure it, add your own Google account, and
   set the publishing status to **In production**.
4. **APIs & Services → Credentials → Create credentials → OAuth client ID**, type **Web
   application**. Under *Authorised redirect URIs*, add the address the settings screen shows —
   `https://<your-domain>/settings` in production, `http://localhost:5173/settings` for local
   development. It must match character for character.
5. Copy the **Client ID** and **Client secret** into Settings → Automatic backups, press
   **Connect Google account**, and approve the consent screen.
6. Press **Test destination** to prove the connection works before relying on it.

### Step 3 is not optional

While the consent screen stays in **Testing**, Google expires the refresh token after **seven
days**. The schedule then fails every slot, and the only place that says so is the run history.
Set it to *In production*.

The scopes requested are `drive.file` and `userinfo.email`, both non-sensitive, so the
application needs no Google verification or security assessment. `drive.file` grants access
**only to files the application itself created** — it cannot read the rest of the Drive. That is
also why the destination folder is created by the app rather than picked from an existing one: a
folder it did not create is invisible under this scope. As a side effect, retention can only ever
see the app's own archives, so it can never delete anything else.

### Renaming the destination folder

Changing the folder name clears the remembered folder id, and the next run creates the folder
under the new name. Copies already in the old folder stay there and are no longer counted
against retention.

## Restoring, and why Drive disconnects

`backup_settings.drive_client_secret` and `drive_refresh_token` are in `REDACTED_COLUMNS`, so
they are **not** in the archive. An archive that carried them would hand over the Google account
the archives themselves are kept in — and it would do it inside a file that is copied off the
server by design.

The consequence is that a restore reloads a schedule that is switched on and points at a Drive
it can no longer reach. The import analysis warns about exactly this, and the fix is to press
**Connect Google account** again after restoring.

## Where the pieces are

| Concern | File |
| --- | --- |
| Schedule slots, "is a copy due" | [schedule.py](../apps/api-server/src/modules/backup/schedule.py) |
| Taking one backup, recording the attempt | [runner.py](../apps/api-server/src/modules/backup/runner.py) |
| Writing to a folder / to Drive, retention | [destinations.py](../apps/api-server/src/modules/backup/destinations.py) |
| OAuth and the Drive HTTP calls | [google_drive.py](../apps/api-server/src/modules/backup/google_drive.py) |
| The thread and its advisory lock | [backup_scheduler.py](../apps/api-server/src/infrastructure/tasks/backup_scheduler.py) |
| Endpoints | [backup/router.py](../apps/api-server/src/modules/backup/router.py) |
| Admin UI | [ScheduledBackupCard.vue](../apps/web-client/src/components/ScheduledBackupCard.vue) |
| Tests | [test_scheduled_backups.py](../apps/api-server/tests/test_scheduled_backups.py) |

## Endpoints

All administrator-only, like the rest of the `backup` module.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/backup/schedule` | The schedule, the next slot, and the last attempts. Never returns a credential. |
| PUT | `/backup/schedule` | Update it. Refuses to enable a Drive schedule before Drive is connected. |
| POST | `/backup/schedule/run-now` | Take a copy now. A failure comes back as a run with its error, not as an HTTP error. |
| GET | `/backup/runs` | The last 50 attempts. |
| POST | `/backup/destination/test` | Prove the destination can receive a copy without producing one. |
| POST | `/backup/drive/authorize` | Store the OAuth client, return the consent URL and a `state`. |
| POST | `/backup/drive/connect` | Exchange the consent code for a refresh token, create the folder. |
| POST | `/backup/drive/disconnect` | Forget the credentials; a Drive schedule is switched off rather than left failing. |

The `state` is generated by the API and compared by the browser against what it stored before
leaving for Google. Without that check, a crafted `?code=` link would connect the installation
to a stranger's Drive, and every backup from then on would be uploaded to it.

## Environment

| Variable | Default | Meaning |
| --- | --- | --- |
| `BACKUP_SCHEDULER_ENABLED` | `true` | Whether this deployment runs the thread at all. The schedule itself is off until an administrator turns it on. |
| `BACKUP_SCHEDULER_INTERVAL_MINUTES` | `15` | How often the thread checks the clock — the schedule's precision. |
| `BACKUP_LOCAL_DIRECTORY` | `/var/backups/pawn-platform` | Default folder for the local destination. In Docker this is the `backup_data` volume. |
