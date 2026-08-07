"""The recurring backup: the schedule, when a slot is due, and what a run records.

The invariants here are about a job nobody watches. A backup that silently stopped happening
looks exactly like one that is working, so most of these tests are about the schedule being
*readable after the fact*: a missed slot gets taken, a repeated failure stops retrying but
stays visible, and a manual copy never passes itself off as the scheduled one.
"""

import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.infrastructure.config.settings import get_settings
from src.infrastructure.persistence.models import AuditLog, BackupRun, BackupSettings, User
from src.infrastructure.security.password import get_password_hash
from src.infrastructure.tasks.backup_scheduler import run_due_backup
from src.modules.backup import google_drive
from src.modules.backup.destinations import ARCHIVE_NAME_PATTERN, store_in_directory
from src.modules.backup.schedule import (
    MAX_ATTEMPTS_PER_SLOT,
    is_backup_due,
    last_due_slot,
    next_run_at,
    to_naive_utc,
)
from src.modules.backup.service import build_export_archive

BOGOTA = ZoneInfo("America/Bogota")


def _settings(**overrides) -> BackupSettings:
    """An unsaved settings row, for the pure slot arithmetic."""
    defaults = {
        "id": 1,
        "enabled": True,
        "frequency": "daily",
        "hour": 2,
        "day_of_week": 1,
        "day_of_month": 1,
        "destination": "local_directory",
        "retention_copies": 7,
        "drive_folder_name": "PawnPlatform Backups",
    }
    return BackupSettings(**{**defaults, **overrides})


def _configure(client: TestClient, headers: dict[str, str], **overrides) -> dict:
    payload = {
        "enabled": False,
        "frequency": "daily",
        "hour": 2,
        "day_of_week": 1,
        "day_of_month": 1,
        "destination": "local_directory",
        "local_directory": None,
        "retention_copies": 7,
        "drive_folder_name": "PawnPlatform Backups",
    }
    payload.update(overrides)
    response = client.put("/api/v1/backup/schedule", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _make_user(db_session: Session, username: str, role: str) -> None:
    db_session.add(
        User(
            username=username,
            hashed_password=get_password_hash("secret123"),
            role=role,
            is_active=True,
        )
    )
    db_session.commit()


def _headers_for(client: TestClient, username: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": "secret123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_the_schedule_starts_disabled(client: TestClient, auth_headers: dict[str, str]) -> None:
    """A backup destination is a decision, so nothing is scheduled until one is made."""
    response = client.get("/api/v1/backup/schedule", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["next_run_at"] is None
    assert body["last_run"] is None
    assert body["drive_connected"] is False


def test_only_administrators_reach_the_schedule(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    """Same reasoning as the rest of the backup module: this reads out the whole database."""
    for username, role in (("officer", "loan_officer"), ("collector", "collector")):
        _make_user(db_session, username, role)
        headers = _headers_for(client, username)

        assert client.get("/api/v1/backup/schedule", headers=headers).status_code == 403
        assert client.get("/api/v1/backup/runs", headers=headers).status_code == 403
        assert client.post("/api/v1/backup/schedule/run-now", headers=headers).status_code == 403


def test_the_schedule_is_stored_and_read_back(client: TestClient, auth_headers: dict[str, str]) -> None:
    body = _configure(
        client,
        auth_headers,
        enabled=True,
        frequency="weekly",
        hour=3,
        day_of_week=5,
        retention_copies=4,
    )

    assert body["enabled"] is True
    assert body["frequency"] == "weekly"
    assert body["retention_copies"] == 4

    next_run = datetime.fromisoformat(body["next_run_at"])
    assert next_run.isoweekday() == 5
    assert next_run.hour == 3

    reread = client.get("/api/v1/backup/schedule", headers=auth_headers).json()
    assert reread["frequency"] == "weekly"
    assert reread["day_of_week"] == 5


def test_an_unknown_frequency_or_destination_is_refused(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    for field, value in (("frequency", "hourly"), ("destination", "dropbox")):
        payload = {
            "enabled": False,
            "frequency": "daily",
            "hour": 2,
            "day_of_week": 1,
            "day_of_month": 1,
            "destination": "local_directory",
            "retention_copies": 7,
        }
        payload[field] = value
        assert client.put("/api/v1/backup/schedule", headers=auth_headers, json=payload).status_code == 422


def test_drive_cannot_be_scheduled_before_it_is_connected(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Otherwise the screen reports a protected installation that produces nothing."""
    response = client.put(
        "/api/v1/backup/schedule",
        headers=auth_headers,
        json={
            "enabled": True,
            "frequency": "daily",
            "hour": 2,
            "day_of_week": 1,
            "day_of_month": 1,
            "destination": "google_drive",
            "retention_copies": 7,
        },
    )

    assert response.status_code == 400
    assert "Connect a Google account" in response.json()["detail"]


def test_the_schedule_never_returns_a_credential(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    """The whole reason these columns are not on `GlobalSettings`."""
    client.get("/api/v1/backup/schedule", headers=auth_headers)
    settings = db_session.get(BackupSettings, 1)
    settings.drive_client_id = "client-id-value"
    settings.drive_client_secret = "client-secret-value"
    settings.drive_refresh_token = "refresh-token-value"
    settings.drive_account_email = "owner@example.com"
    db_session.commit()

    raw = client.get("/api/v1/backup/schedule", headers=auth_headers).text

    assert "client-secret-value" not in raw
    assert "refresh-token-value" not in raw
    assert "client-id-value" not in raw
    # The account is shown on purpose: the administrator has to be able to tell whose Drive
    # the copies are going to.
    assert "owner@example.com" in raw
    assert '"drive_connected":true' in raw.replace(" ", "")


def test_a_manual_run_writes_a_real_archive_and_records_it(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
    create_loan,
    tmp_path: Path,
) -> None:
    create_loan(principal=1000.0)
    _configure(client, auth_headers, local_directory=str(tmp_path))

    response = client.post("/api/v1/backup/schedule/run-now", headers=auth_headers)

    assert response.status_code == 200, response.text
    run = response.json()
    assert run["status"] == "success"
    assert run["trigger"] == "manual"
    assert run["triggered_by"] == "admin"
    assert run["total_rows"] > 0

    written = list(tmp_path.glob("*.zip"))
    assert len(written) == 1
    assert ARCHIVE_NAME_PATTERN.match(written[0].name)
    assert written[0].stat().st_size == run["size_bytes"]

    # A real archive, not just a file of the right name.
    with zipfile.ZipFile(written[0]) as archive:
        assert "manifest.json" in archive.namelist()
        assert "data/loans.json" in archive.namelist()

    # Nothing partial is left behind.
    assert not list(tmp_path.glob(".*partial"))

    stored = db_session.scalars(select(BackupRun)).all()
    assert len(stored) == 1
    assert stored[0].location == str(written[0])

    audit = db_session.scalars(select(AuditLog).where(AuditLog.action == "backup_success")).all()
    assert len(audit) == 1
    assert f"file={run['filename']}" in audit[0].new_data


def test_a_failing_destination_is_recorded_instead_of_raising(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    """The failure is the outcome, and the run history is where it has to be readable.

    A 500 here would leave nothing behind: the next administrator to look would see a
    schedule that appears configured and no record of it never having worked.
    """
    _configure(client, auth_headers, destination="google_drive")

    response = client.post("/api/v1/backup/schedule/run-now", headers=auth_headers)

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "failed"
    assert "Google Drive is not connected" in run["error"]
    assert run["location"] is None

    stored = db_session.scalars(select(BackupRun)).all()
    assert len(stored) == 1
    assert stored[0].status == "failed"

    audit = db_session.scalars(select(AuditLog).where(AuditLog.action == "backup_failed")).all()
    assert len(audit) == 1

    # And the history endpoint shows it, newest first.
    history = client.get("/api/v1/backup/runs", headers=auth_headers).json()
    assert [item["status"] for item in history] == ["failed"]


def test_retention_keeps_the_newest_copies_and_leaves_other_files_alone(
    db_session: Session, tmp_path: Path
) -> None:
    """Pruning is scoped to archives this application produced.

    The destination folder is an operator's folder: it may hold anything. A retention sweep
    that deletes a stranger's file is worse than one that keeps a copy too many.
    """
    for stamp in ("20260101-010000", "20260102-010000", "20260103-010000"):
        (tmp_path / f"acme-export-{stamp}.zip").write_bytes(b"old")

    foreign = tmp_path / "escrituras-notaria.zip"
    foreign.write_bytes(b"not ours")

    archive = build_export_archive(db_session, generated_by="test")
    try:
        stored = store_in_directory(archive, str(tmp_path), retention_copies=2)
    finally:
        archive.stream.close()

    remaining = sorted(path.name for path in tmp_path.glob("*.zip"))
    assert foreign.name in remaining
    assert stored.pruned == 2
    # The new copy plus the newest of the old ones.
    assert Path(stored.location).name in remaining
    assert "acme-export-20260103-010000.zip" in remaining
    assert "acme-export-20260101-010000.zip" not in remaining


def test_retention_of_zero_keeps_everything(db_session: Session, tmp_path: Path) -> None:
    for stamp in ("20260101-010000", "20260102-010000"):
        (tmp_path / f"acme-export-{stamp}.zip").write_bytes(b"old")

    archive = build_export_archive(db_session, generated_by="test")
    try:
        stored = store_in_directory(archive, str(tmp_path), retention_copies=0)
    finally:
        archive.stream.close()

    assert stored.pruned == 0
    assert len(list(tmp_path.glob("*.zip"))) == 3


def test_the_export_redacts_the_drive_credentials(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    """An archive carrying these hands over the destination the archives are kept in."""
    client.get("/api/v1/backup/schedule", headers=auth_headers)
    settings = db_session.get(BackupSettings, 1)
    settings.drive_client_secret = "client-secret-value"
    settings.drive_refresh_token = "refresh-token-value"
    db_session.commit()

    response = client.get("/api/v1/backup/export", headers=auth_headers)
    assert response.status_code == 200

    import io

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        rows = archive.read("data/backup_settings.json").decode("utf-8")
        manifest = archive.read("manifest.json").decode("utf-8")

    assert "client-secret-value" not in rows
    assert "refresh-token-value" not in rows
    assert "backup_settings.drive_refresh_token" in manifest


def test_restoring_an_archive_warns_that_drive_must_be_reconnected(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    """Otherwise the schedule comes back enabled and pointed at a Drive it cannot reach.

    The credentials are redacted from the archive on purpose, so this warning is the only thing
    standing between a restore and a recurring backup that silently stopped.
    """
    client.get("/api/v1/backup/schedule", headers=auth_headers)
    settings = db_session.get(BackupSettings, 1)
    settings.destination = "google_drive"
    settings.drive_client_id = "client"
    settings.drive_client_secret = "secret"
    settings.drive_refresh_token = "refresh"
    db_session.commit()

    export = client.get("/api/v1/backup/export", headers=auth_headers)
    assert export.status_code == 200

    analysis = client.post(
        "/api/v1/backup/import",
        headers=auth_headers,
        files={"file": ("export.zip", export.content, "application/zip")},
        data={"validate_only": "true"},
    ).json()

    assert any("Reconnect the Google" in warning for warning in analysis["warnings"])


def test_the_daily_slot_walks_back_to_the_last_one_that_passed() -> None:
    settings = _settings(frequency="daily", hour=2)

    # Before today's slot, the last one due is yesterday's.
    morning = datetime(2026, 8, 5, 1, 30, tzinfo=BOGOTA)
    assert last_due_slot(settings, morning) == datetime(2026, 8, 4, 2, 0, tzinfo=BOGOTA)
    assert next_run_at(settings, morning) == datetime(2026, 8, 5, 2, 0, tzinfo=BOGOTA)

    # After it, today's.
    evening = datetime(2026, 8, 5, 23, 0, tzinfo=BOGOTA)
    assert last_due_slot(settings, evening) == datetime(2026, 8, 5, 2, 0, tzinfo=BOGOTA)
    assert next_run_at(settings, evening) == datetime(2026, 8, 6, 2, 0, tzinfo=BOGOTA)


def test_the_weekly_slot_lands_on_the_chosen_weekday() -> None:
    # 2026-08-05 is a Wednesday.
    settings = _settings(frequency="weekly", hour=4, day_of_week=1)

    reference = datetime(2026, 8, 5, 10, 0, tzinfo=BOGOTA)
    assert last_due_slot(settings, reference) == datetime(2026, 8, 3, 4, 0, tzinfo=BOGOTA)
    assert next_run_at(settings, reference) == datetime(2026, 8, 10, 4, 0, tzinfo=BOGOTA)

    # On the day itself, before the hour, the slot due is still the previous week's.
    early = datetime(2026, 8, 3, 1, 0, tzinfo=BOGOTA)
    assert last_due_slot(settings, early) == datetime(2026, 7, 27, 4, 0, tzinfo=BOGOTA)
    assert next_run_at(settings, early) == datetime(2026, 8, 3, 4, 0, tzinfo=BOGOTA)


def test_the_monthly_slot_crosses_the_year() -> None:
    settings = _settings(frequency="monthly", hour=5, day_of_month=10)

    reference = datetime(2026, 1, 3, 9, 0, tzinfo=BOGOTA)
    assert last_due_slot(settings, reference) == datetime(2025, 12, 10, 5, 0, tzinfo=BOGOTA)
    assert next_run_at(settings, reference) == datetime(2026, 1, 10, 5, 0, tzinfo=BOGOTA)

    after = datetime(2026, 12, 20, 9, 0, tzinfo=BOGOTA)
    assert next_run_at(settings, after) == datetime(2027, 1, 10, 5, 0, tzinfo=BOGOTA)


def test_a_slot_the_server_slept_through_is_still_due(db_session: Session) -> None:
    """The point of comparing against the slot rather than "did we run recently".

    A droplet that was down at 2am must take the copy when it comes back, and take one.
    """
    settings = _settings(frequency="daily", hour=2)
    now_local = datetime.now(BOGOTA).replace(hour=9, minute=0, second=0, microsecond=0)

    assert is_backup_due(db_session, settings, now_local) is True

    # A copy from before the slot does not satisfy it.
    stale = to_naive_utc(last_due_slot(settings, now_local)) - timedelta(hours=1)
    db_session.add(BackupRun(started_at=stale, status="success", trigger="scheduled"))
    db_session.commit()
    assert is_backup_due(db_session, settings, now_local) is True

    # One from inside the slot does.
    fresh = to_naive_utc(last_due_slot(settings, now_local)) + timedelta(minutes=5)
    db_session.add(BackupRun(started_at=fresh, status="success", trigger="scheduled"))
    db_session.commit()
    assert is_backup_due(db_session, settings, now_local) is False


def test_a_manual_copy_does_not_satisfy_the_schedule(db_session: Session) -> None:
    """A manual run is an extra copy, not the scheduled one.

    Counting it would let a manual run at 1am cancel the 2am copy, with nothing saying so.
    """
    settings = _settings(frequency="daily", hour=2)
    now_local = datetime.now(BOGOTA).replace(hour=9, minute=0, second=0, microsecond=0)

    inside_slot = to_naive_utc(last_due_slot(settings, now_local)) + timedelta(minutes=5)
    db_session.add(BackupRun(started_at=inside_slot, status="success", trigger="manual"))
    db_session.commit()

    assert is_backup_due(db_session, settings, now_local) is True


def test_a_failing_slot_is_retried_a_few_times_and_then_left_alone(db_session: Session) -> None:
    """Without the cap, a revoked Drive token writes a run row every fifteen minutes.

    Hundreds of identical failures bury the first one, which is the row that says what broke.
    """
    settings = _settings(frequency="daily", hour=2)
    now_local = datetime.now(BOGOTA).replace(hour=9, minute=0, second=0, microsecond=0)
    inside_slot = to_naive_utc(last_due_slot(settings, now_local)) + timedelta(minutes=1)

    for attempt in range(MAX_ATTEMPTS_PER_SLOT - 1):
        db_session.add(
            BackupRun(
                started_at=inside_slot + timedelta(minutes=attempt),
                status="failed",
                trigger="scheduled",
                error="Google Drive rejected the request",
            )
        )
    db_session.commit()
    assert is_backup_due(db_session, settings, now_local) is True

    db_session.add(
        BackupRun(started_at=inside_slot + timedelta(hours=1), status="failed", trigger="scheduled")
    )
    db_session.commit()
    assert is_backup_due(db_session, settings, now_local) is False

    # The next slot starts over, so a schedule that failed today still tries tomorrow.
    tomorrow = now_local + timedelta(days=1)
    assert is_backup_due(db_session, settings, tomorrow) is True


def test_the_scheduler_takes_the_due_copy_exactly_once(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    """What the background thread actually calls, end to end.

    Hour 0 puts the slot earlier today whatever the time is, so the first check is always due.
    The second must not produce a second copy: the thread wakes every fifteen minutes, and a
    check that ignored the run it just wrote would back up all day.
    """
    _configure(client, auth_headers, enabled=True, hour=0, local_directory=str(tmp_path))

    first = run_due_backup(db_session=db_session)

    assert first is not None
    assert first.status == "success"
    assert first.trigger == "scheduled"
    assert first.triggered_by is None
    assert len(list(tmp_path.glob("*.zip"))) == 1

    assert run_due_backup(db_session=db_session) is None
    assert len(list(tmp_path.glob("*.zip"))) == 1


def test_the_scheduler_does_nothing_while_the_schedule_is_off(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    _configure(client, auth_headers, enabled=False, hour=0, local_directory=str(tmp_path))

    assert run_due_backup(db_session=db_session) is None
    assert list(tmp_path.glob("*.zip")) == []
    assert db_session.scalars(select(BackupRun)).all() == []


def test_a_disabled_schedule_is_never_due(db_session: Session) -> None:
    settings = _settings(enabled=False)
    assert is_backup_due(db_session, settings, datetime.now(BOGOTA)) is False


def test_disconnecting_drive_turns_off_a_schedule_pointed_at_it(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    """Leaving it enabled would fail every slot from then on."""
    client.get("/api/v1/backup/schedule", headers=auth_headers)
    settings = db_session.get(BackupSettings, 1)
    settings.drive_client_id = "client"
    settings.drive_client_secret = "secret"
    settings.drive_refresh_token = "refresh"
    settings.drive_account_email = "owner@example.com"
    settings.destination = "google_drive"
    settings.enabled = True
    db_session.commit()

    response = client.post("/api/v1/backup/drive/disconnect", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["drive_connected"] is False
    assert body["enabled"] is False
    assert body["destination"] == "local_directory"
    assert body["drive_account_email"] is None


def test_an_unset_directory_keeps_following_the_deployment_default(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Saving the resolved path back would pin the old one the day a deploy moves the volume."""
    body = _configure(client, auth_headers, local_directory=None)

    assert body["local_directory"] == ""
    assert body["local_directory_effective"] == get_settings().backup_local_directory


def test_the_local_destination_test_reports_the_directory(
    client: TestClient, auth_headers: dict[str, str], tmp_path: Path
) -> None:
    _configure(client, auth_headers, local_directory=str(tmp_path / "nested"))

    response = client.post("/api/v1/backup/destination/test", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["detail"].endswith("nested")
    # The probe cleans up after itself.
    assert list((tmp_path / "nested").iterdir()) == []


class _FakeGoogle:
    """Stands in for Google's endpoints so the Drive path is exercised without a network.

    The upload path is the part of this feature that cannot be tried by hand on every change —
    it needs a real Google project — so the shape of the conversation is pinned here instead.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.token_status = 200
        self.stored_folder_status = 200
        self.files: list[dict[str, str]] = []
        self.deleted: list[str] = []
        self.created_folders: list[str] = []
        self.uploaded: list[str] = []
        self._pending_name = ""

    def handle(self, method: str, url: str, **kwargs) -> httpx.Response:
        self.calls.append((method, url))
        params = kwargs.get("params") or {}
        body = kwargs.get("json") or {}

        if url == google_drive.TOKEN_ENDPOINT:
            if self.token_status != 200:
                return httpx.Response(
                    self.token_status,
                    json={"error": "invalid_grant", "error_description": "Token has been expired or revoked."},
                )
            return httpx.Response(200, json={"access_token": "access-token", "refresh_token": "refresh-token"})

        if url == google_drive.USERINFO_ENDPOINT:
            return httpx.Response(200, json={"email": "owner@example.com"})

        if url == google_drive.UPLOAD_ENDPOINT:
            # The resumable session carries the metadata; the bytes follow on the returned URL.
            self._pending_name = str(body.get("name"))
            return httpx.Response(200, headers={"location": "https://upload.example/session-1"})

        if url == "https://upload.example/session-1":
            self.uploaded.append(self._pending_name)
            # As Drive would: the new copy is part of the folder from now on, so retention sees
            # it and counts it among the copies to keep.
            self.files.append(
                {"id": "uploaded-file-id", "name": self._pending_name, "createdTime": "2026-08-05T02:00:00Z"}
            )
            return httpx.Response(200, json={"id": "uploaded-file-id", "name": self._pending_name})

        if url.startswith(f"{google_drive.FILES_ENDPOINT}/"):
            file_id = url.rsplit("/", 1)[1]
            if method == "DELETE":
                self.deleted.append(file_id)
                return httpx.Response(204)
            if self.stored_folder_status != 200:
                return httpx.Response(self.stored_folder_status, json={"error": {"message": "File not found"}})
            return httpx.Response(200, json={"id": file_id, "trashed": False})

        if url == google_drive.FILES_ENDPOINT:
            if method == "POST":
                self.created_folders.append(str(body.get("name")))
                return httpx.Response(200, json={"id": "created-folder-id"})
            if "in parents" in str(params.get("q", "")):
                return httpx.Response(200, json={"files": self.files})
            # Folder lookup by name: nothing pre-existing unless a test says so.
            return httpx.Response(200, json={"files": []})

        raise AssertionError(f"unexpected request {method} {url}")


def _install_fake_google(monkeypatch, fake: _FakeGoogle) -> None:
    class _FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self) -> "_FakeClient":
            return self

        def __exit__(self, *exc_info) -> bool:
            return False

        def request(self, method: str, url: str, **kwargs) -> httpx.Response:
            return fake.handle(method, url, **kwargs)

        def get(self, url: str, **kwargs) -> httpx.Response:
            return fake.handle("GET", url, **kwargs)

        def post(self, url: str, **kwargs) -> httpx.Response:
            return fake.handle("POST", url, **kwargs)

        def put(self, url: str, **kwargs) -> httpx.Response:
            return fake.handle("PUT", url, **kwargs)

    monkeypatch.setattr(google_drive.httpx, "Client", _FakeClient)


def _connect_drive(db_session: Session, destination: str = "google_drive", folder_id: str | None = None) -> None:
    settings = db_session.get(BackupSettings, 1) or BackupSettings(id=1)
    settings.id = 1
    settings.drive_client_id = "client-id"
    settings.drive_client_secret = "client-secret"
    settings.drive_refresh_token = "refresh-token"
    settings.drive_folder_id = folder_id
    settings.destination = destination
    db_session.add(settings)
    db_session.commit()


def test_a_drive_backup_uploads_and_prunes(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], monkeypatch
) -> None:
    client.get("/api/v1/backup/schedule", headers=auth_headers)
    _connect_drive(db_session)

    fake = _FakeGoogle()
    fake.files = [
        {"id": "old-1", "name": "acme-export-20260101-010000.zip", "createdTime": "2026-01-01T01:00:00Z"},
        {"id": "old-2", "name": "acme-export-20260102-010000.zip", "createdTime": "2026-01-02T01:00:00Z"},
        {"id": "old-3", "name": "acme-export-20260103-010000.zip", "createdTime": "2026-01-03T01:00:00Z"},
        {"id": "foreign", "name": "escrituras.zip", "createdTime": "2020-01-01T01:00:00Z"},
    ]
    _install_fake_google(monkeypatch, fake)

    settings = db_session.get(BackupSettings, 1)
    settings.retention_copies = 2
    db_session.commit()

    run = client.post("/api/v1/backup/schedule/run-now", headers=auth_headers).json()

    assert run["status"] == "success", run["error"]
    assert run["destination"] == "google_drive"
    assert run["location"] == "uploaded-file-id"
    assert fake.uploaded == [run["filename"]]

    # Only the app's own archives are pruned, oldest first, and never the foreign file.
    assert sorted(fake.deleted) == ["old-1", "old-2"]

    # The folder it had to create is remembered, so later runs do not look it up again.
    assert fake.created_folders == ["PawnPlatform Backups"]
    assert db_session.get(BackupSettings, 1).drive_folder_id == "created-folder-id"


def test_a_drive_folder_the_operator_deleted_is_recreated(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], monkeypatch
) -> None:
    """A 404 on the remembered folder must not become a permanent failure.

    The alternative is every run from then on reporting "File not found", which reads like a
    permission problem and cannot be fixed from the settings screen.
    """
    client.get("/api/v1/backup/schedule", headers=auth_headers)
    _connect_drive(db_session, folder_id="folder-that-is-gone")

    fake = _FakeGoogle()
    fake.stored_folder_status = 404
    _install_fake_google(monkeypatch, fake)

    run = client.post("/api/v1/backup/schedule/run-now", headers=auth_headers).json()

    assert run["status"] == "success", run["error"]
    assert fake.created_folders == ["PawnPlatform Backups"]
    assert db_session.get(BackupSettings, 1).drive_folder_id == "created-folder-id"


def test_a_transient_drive_error_does_not_scatter_folders(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], monkeypatch
) -> None:
    """Only a 404 means "gone". Treating a 500 as missing would create a folder per outage."""
    client.get("/api/v1/backup/schedule", headers=auth_headers)
    _connect_drive(db_session, folder_id="folder-abc")

    fake = _FakeGoogle()
    fake.stored_folder_status = 500
    _install_fake_google(monkeypatch, fake)

    run = client.post("/api/v1/backup/schedule/run-now", headers=auth_headers).json()

    assert run["status"] == "failed"
    assert fake.created_folders == []
    assert db_session.get(BackupSettings, 1).drive_folder_id == "folder-abc"


def test_a_revoked_authorization_is_reported_in_google_s_own_words(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], monkeypatch
) -> None:
    """This is the failure the 7-day "Testing" consent screen produces, and the run history is
    the only place it can be read. A generic message would leave the operator with nothing to
    act on."""
    client.get("/api/v1/backup/schedule", headers=auth_headers)
    _connect_drive(db_session)

    fake = _FakeGoogle()
    fake.token_status = 400
    _install_fake_google(monkeypatch, fake)

    run = client.post("/api/v1/backup/schedule/run-now", headers=auth_headers).json()

    assert run["status"] == "failed"
    assert "expired or revoked" in run["error"]

    # And the destination test says the same thing, without producing a copy.
    result = client.post("/api/v1/backup/destination/test", headers=auth_headers).json()
    assert result["ok"] is False
    assert "expired or revoked" in result["detail"]


def test_renaming_the_drive_folder_drops_the_remembered_id(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    """The id belongs to the old name; keeping it uploads somewhere the operator forgot."""
    client.get("/api/v1/backup/schedule", headers=auth_headers)
    settings = db_session.get(BackupSettings, 1)
    settings.drive_folder_id = "folder-abc"
    db_session.commit()

    body = _configure(client, auth_headers, drive_folder_name="Copias PawnPlatform")

    assert body["drive_folder_name"] == "Copias PawnPlatform"
    assert body["drive_folder_id"] is None
