import io
import json
import zipfile
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import Customer, InterestCharge, Loan, Payment, User
from src.infrastructure.security.password import get_password_hash
from src.modules.backup.restore import IMPORT_CONFIRMATION

CURRENT_REVISION = "20260725_0006"


def _stamp_schema_revision(db_session: Session, revision: str = CURRENT_REVISION) -> None:
    """Give the test database an Alembic revision so schema checks can run on it."""
    db_session.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"))
    db_session.execute(text("DELETE FROM alembic_version"))
    db_session.execute(text("INSERT INTO alembic_version (version_num) VALUES (:revision)"), {"revision": revision})
    db_session.commit()


def _export_bytes(client: TestClient, auth_headers: dict[str, str]) -> bytes:
    response = client.get("/api/v1/backup/export", headers=auth_headers)
    assert response.status_code == 200
    return response.content


def _post_import(
    client: TestClient,
    auth_headers: dict[str, str],
    content: bytes,
    *,
    confirmation: str = IMPORT_CONFIRMATION,
    validate_only: bool = False,
    filename: str = "export.zip",
):
    return client.post(
        "/api/v1/backup/import",
        headers=auth_headers,
        files={"file": (filename, content, "application/zip")},
        data={"confirmation": confirmation, "validate_only": str(validate_only).lower()},
    )


def _rewrite_archive(content: bytes, changes: dict[str, bytes]) -> bytes:
    """Rebuild an archive replacing the given entries."""
    source = zipfile.ZipFile(io.BytesIO(content))
    target_buffer = io.BytesIO()
    with zipfile.ZipFile(target_buffer, "w", zipfile.ZIP_DEFLATED) as target:
        for name in source.namelist():
            target.writestr(name, changes.get(name, source.read(name)))
    return target_buffer.getvalue()


def test_validate_only_reports_the_plan_without_touching_data(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    create_loan(principal=1000)
    content = _export_bytes(client, auth_headers)
    loans_before = db_session.query(Loan).count()

    response = _post_import(client, auth_headers, content, validate_only=True)
    assert response.status_code == 200
    payload = response.json()

    assert payload["imported"] is False
    assert payload["can_import"] is True
    assert payload["format_version"] == "1.0"
    assert any("replaced" in warning for warning in payload["warnings"])

    # Business tables match exactly. audit_logs is the exception: exporting is itself an
    # audited action, so the database gained a row after the archive was built.
    for plan in payload["tables"]:
        if plan["name"] == "audit_logs":
            assert plan["current_rows"] > plan["incoming_rows"]
        else:
            assert plan["current_rows"] == plan["incoming_rows"], plan

    loans_plan = next(item for item in payload["tables"] if item["name"] == "loans")
    assert loans_plan["current_rows"] == loans_before

    db_session.expire_all()
    assert db_session.query(Loan).count() == loans_before


def test_import_restores_data_after_it_was_deleted(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1500)
    charge = InterestCharge(
        loan_id=loan["id"],
        period_start=date.today() - timedelta(days=30),
        period_end=date.today(),
        charge_date=date.today(),
        amount=150.0,
        status="generated",
    )
    db_session.add(charge)
    db_session.commit()

    content = _export_bytes(client, auth_headers)
    expected_customers = db_session.query(Customer).count()
    expected_loans = db_session.query(Loan).count()
    expected_charges = db_session.query(InterestCharge).count()

    # Wipe the business data the way a disaster would.
    db_session.query(InterestCharge).delete()
    db_session.query(Payment).delete()
    db_session.query(Loan).delete()
    db_session.query(Customer).delete()
    db_session.commit()
    assert db_session.query(Loan).count() == 0

    response = _post_import(client, auth_headers, content)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["imported"] is True

    db_session.expire_all()
    assert db_session.query(Customer).count() == expected_customers
    assert db_session.query(Loan).count() == expected_loans
    assert db_session.query(InterestCharge).count() == expected_charges

    restored = db_session.get(Loan, loan["id"])
    assert restored is not None
    assert restored.principal_amount == 1500
    assert restored.loan_type.value == "pawn"
    assert restored.status.value == "active"
    assert restored.disbursement_date == date.fromisoformat(loan["disbursement_date"])


def test_import_replaces_data_added_after_the_export(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    create_customer,
    db_session: Session,
) -> None:
    create_loan(principal=800)
    content = _export_bytes(client, auth_headers)

    create_customer(document_number="DOC-AFTER-EXPORT")
    assert db_session.query(Customer).filter(Customer.document_number == "DOC-AFTER-EXPORT").count() == 1

    response = _post_import(client, auth_headers, content)
    assert response.status_code == 200, response.text

    db_session.expire_all()
    # The archive is authoritative: rows created after it was taken are gone.
    assert db_session.query(Customer).filter(Customer.document_number == "DOC-AFTER-EXPORT").count() == 0


def test_import_keeps_working_after_restore_by_creating_new_rows(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    create_loan(principal=900)
    content = _export_bytes(client, auth_headers)

    assert _post_import(client, auth_headers, content).status_code == 200

    # Identity sequences must be realigned or this insert collides with a restored id.
    created = client.post(
        "/api/v1/customers",
        headers=auth_headers,
        json={
            "first_name": "Nuevo",
            "last_name": "Cliente",
            "document_type": "ID",
            "document_number": "DOC-POST-IMPORT",
            "phone": "",
            "email": "",
            "address": "",
            "city": "Bogota",
            "status": "active",
        },
    )
    assert created.status_code == 201, created.text


def test_import_requires_the_typed_confirmation(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    create_loan(principal=700)
    content = _export_bytes(client, auth_headers)
    loans_before = db_session.query(Loan).count()

    response = _post_import(client, auth_headers, content, confirmation="yes")
    assert response.status_code == 400
    assert IMPORT_CONFIRMATION in response.json()["detail"]

    db_session.expire_all()
    assert db_session.query(Loan).count() == loans_before


def test_import_rejects_a_schema_revision_mismatch(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    _stamp_schema_revision(db_session)
    create_loan(principal=600)
    content = _export_bytes(client, auth_headers)

    source = zipfile.ZipFile(io.BytesIO(content))
    manifest = json.loads(source.read("manifest.json"))
    assert manifest["schema_revision"] == CURRENT_REVISION
    manifest["schema_revision"] = "some_other_revision"
    tampered = _rewrite_archive(content, {"manifest.json": json.dumps(manifest).encode()})

    response = _post_import(client, auth_headers, tampered, validate_only=True)
    assert response.status_code == 200
    payload = response.json()
    assert payload["can_import"] is False
    assert any("Schema mismatch" in error for error in payload["errors"])

    applied = _post_import(client, auth_headers, tampered)
    assert applied.status_code == 400


def test_import_accepts_a_matching_schema_revision(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    """The path production takes: the revision is recorded and the archive matches it."""
    _stamp_schema_revision(db_session)
    create_loan(principal=650)
    content = _export_bytes(client, auth_headers)

    analysis = _post_import(client, auth_headers, content, validate_only=True)
    assert analysis.status_code == 200
    payload = analysis.json()
    assert payload["archive_schema_revision"] == CURRENT_REVISION
    assert payload["database_schema_revision"] == CURRENT_REVISION
    assert payload["can_import"] is True
    assert payload["errors"] == []

    applied = _post_import(client, auth_headers, content)
    assert applied.status_code == 200
    assert applied.json()["imported"] is True


def test_import_rejects_an_archive_without_an_active_administrator(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
) -> None:
    create_loan(principal=500)
    content = _export_bytes(client, auth_headers)

    source = zipfile.ZipFile(io.BytesIO(content))
    users = json.loads(source.read("data/users.json"))
    for user in users:
        user["is_active"] = False
    tampered = _rewrite_archive(content, {"data/users.json": json.dumps(users).encode()})

    response = _post_import(client, auth_headers, tampered, validate_only=True)
    assert response.status_code == 200
    assert response.json()["can_import"] is False
    assert any("administrator" in error for error in response.json()["errors"])


def test_import_rejects_unknown_columns(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
) -> None:
    create_loan(principal=400)
    content = _export_bytes(client, auth_headers)

    source = zipfile.ZipFile(io.BytesIO(content))
    loans = json.loads(source.read("data/loans.json"))
    for row in loans:
        row["column_from_the_future"] = 1
    tampered = _rewrite_archive(content, {"data/loans.json": json.dumps(loans).encode()})

    response = _post_import(client, auth_headers, tampered, validate_only=True)
    assert response.json()["can_import"] is False
    assert any("column_from_the_future" in error for error in response.json()["errors"])


def test_import_rejects_a_missing_table(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
) -> None:
    create_loan(principal=300)
    content = _export_bytes(client, auth_headers)

    source = zipfile.ZipFile(io.BytesIO(content))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as target:
        for name in source.namelist():
            if name != "data/loans.json":
                target.writestr(name, source.read(name))

    response = _post_import(client, auth_headers, buffer.getvalue(), validate_only=True)
    assert response.json()["can_import"] is False
    assert any("no data for table loans" in error for error in response.json()["errors"])


def test_import_rejects_a_file_that_is_not_a_zip(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = _post_import(client, auth_headers, b"not a zip at all", validate_only=True)
    assert response.status_code == 400
    assert "valid ZIP" in response.json()["detail"]


def test_failed_import_leaves_the_data_untouched(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    create_loan(principal=1000)
    content = _export_bytes(client, auth_headers)
    loans_before = db_session.query(Loan).count()
    customers_before = db_session.query(Customer).count()

    # A row that violates the schema makes the insert fail midway through the restore.
    source = zipfile.ZipFile(io.BytesIO(content))
    loans = json.loads(source.read("data/loans.json"))
    loans.append({**loans[0], "id": loans[0]["id"] + 1000, "loan_type": "not_a_loan_type"})
    tampered = _rewrite_archive(content, {"data/loans.json": json.dumps(loans).encode()})

    response = _post_import(client, auth_headers, tampered)
    assert response.status_code == 400

    # The whole restore runs in one transaction, so nothing was lost.
    db_session.rollback()
    db_session.expire_all()
    assert db_session.query(Loan).count() == loans_before
    assert db_session.query(Customer).count() == customers_before


def test_import_is_restricted_to_administrators(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    content = _export_bytes(client, auth_headers)

    db_session.add(
        User(
            username="officer1",
            hashed_password=get_password_hash("secret123"),
            role="loan_officer",
            is_active=True,
        )
    )
    db_session.commit()

    login = client.post("/api/v1/auth/login", json={"username": "officer1", "password": "secret123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    assert _post_import(client, headers, content).status_code == 403
    assert _post_import(client, {}, content).status_code == 401


def test_import_is_audited(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    create_loan(principal=1000)
    content = _export_bytes(client, auth_headers)

    assert _post_import(client, auth_headers, content, filename="my-backup.zip").status_code == 200

    from src.infrastructure.persistence.models import AuditLog

    db_session.expire_all()
    entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "import_all_data")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert entry is not None
    assert entry.entity_id == "my-backup.zip"
    assert "rows_after=" in entry.new_data
