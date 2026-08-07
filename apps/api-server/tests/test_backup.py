import csv
import io
import json
import zipfile
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.infrastructure.persistence.database import Base
from src.infrastructure.persistence.models import InterestCharge, Loan, User
from src.infrastructure.security.password import get_password_hash


def _download_export(client: TestClient, auth_headers: dict[str, str]) -> zipfile.ZipFile:
    response = client.get("/api/v1/backup/export", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment; filename=" in response.headers["content-disposition"]
    assert response.headers["content-disposition"].endswith('.zip"')
    return zipfile.ZipFile(io.BytesIO(response.content))


def test_export_contains_every_table_as_json_and_csv(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    archive = _download_export(client, auth_headers)
    names = set(archive.namelist())

    assert "manifest.json" in names
    assert "README.txt" in names

    # Nothing may be left out: every mapped table needs both representations.
    for table in Base.metadata.sorted_tables:
        assert f"data/{table.name}.json" in names
        assert f"csv/{table.name}.csv" in names

    manifest = json.loads(archive.read("manifest.json"))
    assert manifest["format_version"] == "1.0"
    assert {item["name"] for item in manifest["tables"]} == {
        table.name for table in Base.metadata.sorted_tables
    }


def test_export_preserves_all_columns_and_values(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1234.56)
    charge = InterestCharge(
        loan_id=loan["id"],
        period_start=date.today() - timedelta(days=30),
        period_end=date.today(),
        charge_date=date.today(),
        amount=123.45,
        status="generated",
    )
    db_session.add(charge)
    db_session.commit()

    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    archive = _download_export(client, auth_headers)

    loans = json.loads(archive.read("data/loans.json"))
    exported_loan = next(item for item in loans if item["id"] == loan["id"])
    # Every mapped column of the table is present, including recently added ones.
    assert set(exported_loan) == {column.name for column in Loan.__table__.columns}
    assert exported_loan["principal_amount"] == 1234.56
    assert exported_loan["loan_type"] == "pawn"
    assert exported_loan["status"] == "active"
    assert exported_loan["disbursement_date"] == loan_db.disbursement_date.isoformat()

    charges = json.loads(archive.read("data/interest_charges.json"))
    assert any(item["amount"] == 123.45 and item["status"] == "generated" for item in charges)

    manifest = json.loads(archive.read("manifest.json"))
    counts = {item["name"]: item["rows"] for item in manifest["tables"]}
    assert counts["loans"] == db_session.query(Loan).count()
    assert counts["interest_charges"] == db_session.query(InterestCharge).count()
    assert manifest["total_rows"] == sum(counts.values())


def test_export_csv_matches_json_rows(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
) -> None:
    create_customer(document_number="DOC-CSV")

    archive = _download_export(client, auth_headers)

    customers_json = json.loads(archive.read("data/customers.json"))
    csv_text = archive.read("csv/customers.csv").decode("utf-8-sig")
    customers_csv = list(csv.DictReader(io.StringIO(csv_text)))

    assert len(customers_csv) == len(customers_json)
    assert customers_csv[0]["document_number"] == customers_json[0]["document_number"]


def test_export_redacts_live_password_reset_tokens(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    user = db_session.query(User).first()
    assert user is not None
    user.reset_token = "live-token-value"
    user.reset_token_expires_at = None
    db_session.commit()

    archive = _download_export(client, auth_headers)
    users = json.loads(archive.read("data/users.json"))

    assert all(item["reset_token"] is None for item in users)
    assert "live-token-value" not in archive.read("data/users.json").decode("utf-8")
    # The hash is kept so the archive is a real backup, and the README warns about it.
    assert any(item["hashed_password"] for item in users)

    manifest = json.loads(archive.read("manifest.json"))
    # Every field the archive withholds is named in the manifest, so whoever restores it knows
    # what they have to set up again rather than discovering it when a backup fails.
    assert manifest["redacted_fields"] == [
        "backup_settings.drive_client_secret",
        "backup_settings.drive_refresh_token",
        "users.reset_token",
        "users.reset_token_expires_at",
    ]


def test_export_is_restricted_to_administrators(
    client: TestClient,
    db_session: Session,
) -> None:
    db_session.add(
        User(
            username="collector1",
            hashed_password=get_password_hash("secret123"),
            role="collector",
            is_active=True,
        )
    )
    db_session.commit()

    login = client.post("/api/v1/auth/login", json={"username": "collector1", "password": "secret123"})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    assert client.get("/api/v1/backup/export", headers=headers).status_code == 403
    assert client.get("/api/v1/backup/export").status_code == 401


def test_export_is_audited(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    _download_export(client, auth_headers)

    from src.infrastructure.persistence.models import AuditLog

    entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "export_all_data")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert entry is not None
    assert entry.entity_id.endswith(".zip")
    assert "rows=" in entry.new_data
