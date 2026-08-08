"""What the recovery email must and must not do.

The mailer is the first thing in this application that reaches outside the process during a
request, and it was wired into the one endpoint built to give nothing away. These pin the
parts that are easy to undo by accident.
"""

import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.infrastructure.config.settings import get_settings
from src.infrastructure.email import client as email_client
from src.infrastructure.email import password_reset
from src.infrastructure.email.client import EmailNotConfigured, EmailSendFailed
from src.infrastructure.persistence.models import User
from src.infrastructure.security.password import get_password_hash


def _configure_mail(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "hostinger_mail_api_token", "test-token", raising=False)
    monkeypatch.setattr(settings, "hostinger_mailbox_resource_id", "ACtest", raising=False)


def _user_with_email(db_session: Session, email: str = "operator@example.com") -> User:
    user = User(
        username="mailuser",
        hashed_password=get_password_hash("secret123"),
        full_name="Mail User",
        email=email,
        role="administrator",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


class _Recorder:
    """Stands in for the transport so nothing leaves the test process."""

    def __init__(self, fail: bool = False) -> None:
        self.sent: list[dict] = []
        self.fail = fail

    def __call__(self, *, to: str, subject: str, html: str, text: str) -> None:
        if self.fail:
            raise EmailSendFailed("Hostinger refused the message (status 403)")
        self.sent.append({"to": to, "subject": subject, "html": html, "text": text})


# ── The transport ────────────────────────────────────────────────────────────────────────


def test_sending_without_credentials_raises_rather_than_returning(monkeypatch) -> None:
    """The first version logged and returned, so an unconfigured installation looked healthy.

    A caller that wants to carry on regardless has to catch this; it must not be the default.
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "hostinger_mail_api_token", "", raising=False)
    monkeypatch.setattr(settings, "hostinger_mailbox_resource_id", "", raising=False)

    assert email_client.email_is_configured() is False

    with pytest.raises(EmailNotConfigured):
        email_client.send_email(to="a@b.co", subject="s", html="<p>h</p>", text="t")


def test_half_configured_counts_as_unconfigured(monkeypatch) -> None:
    """A token with no mailbox id is the shape that produced a 403 and looked like a bad token."""
    settings = get_settings()
    monkeypatch.setattr(settings, "hostinger_mail_api_token", "test-token", raising=False)
    monkeypatch.setattr(settings, "hostinger_mailbox_resource_id", "", raising=False)

    assert email_client.email_is_configured() is False


# ── The message ──────────────────────────────────────────────────────────────────────────


def test_the_link_points_at_the_web_client_and_carries_the_token(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "frontend_url", "https://mutuum.example.com/", raising=False)

    subject, html, text = password_reset.build_message("tok-123", "es")

    expected = "https://mutuum.example.com/reset-password?token=tok-123"
    assert expected in html
    assert expected in text, "the plain-text part must carry the link too, not just the HTML"
    assert subject


def test_locale_comes_from_the_client_then_the_header_then_spanish() -> None:
    assert password_reset.normalise_locale("en", None) == "en"
    assert password_reset.normalise_locale(None, "en-GB,en;q=0.9") == "en"
    assert password_reset.normalise_locale(None, None) == "es"

    # A header naming a language we do not write falls back to Spanish rather than matching
    # on the *region* subtag: a substring search for "en" finds one in "fr-ES,fr;q=0.9" and
    # would have written to a French speaker in English.
    assert password_reset.normalise_locale(None, "fr-ES,fr;q=0.9") == "es"
    assert password_reset.normalise_locale("en", "es-CO") == "en", "the explicit choice wins"
    assert password_reset.normalise_locale("", "en-US") == "en", "an empty choice is not a choice"


def test_both_languages_are_written(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "frontend_url", "https://x.test", raising=False)

    es_subject, es_html, _ = password_reset.build_message("t", "es")
    en_subject, en_html, _ = password_reset.build_message("t", "en")

    assert es_subject != en_subject
    assert "contraseña" in es_html.lower()
    assert "password" in en_html.lower()


def test_a_send_failure_is_logged_not_raised(monkeypatch) -> None:
    """It runs as a background task; raising there would die where nobody sees it."""
    monkeypatch.setattr(password_reset, "send_email", _Recorder(fail=True))
    monkeypatch.setattr(get_settings(), "frontend_url", "https://x.test", raising=False)

    password_reset.send_password_reset_email("a@b.co", "tok", "es")  # must not raise


# ── The endpoint ─────────────────────────────────────────────────────────────────────────


def test_forgot_password_sends_to_the_matched_account(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    _configure_mail(monkeypatch)
    recorder = _Recorder()
    monkeypatch.setattr(password_reset, "send_email", recorder)
    monkeypatch.setattr(get_settings(), "frontend_url", "https://x.test", raising=False)

    _user_with_email(db_session, "operator@example.com")

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"username_or_email": "operator@example.com", "locale": "en"},
    )
    assert response.status_code == 200

    assert len(recorder.sent) == 1, "exactly one message, to the account that matched"
    assert recorder.sent[0]["to"] == "operator@example.com"
    assert response.json()["reset_token"] in recorder.sent[0]["text"]


def test_an_unknown_identifier_sends_nothing_and_says_the_same_thing(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    """The wording was always identical; the mailer is what could have given it away."""
    _configure_mail(monkeypatch)
    recorder = _Recorder()
    monkeypatch.setattr(password_reset, "send_email", recorder)

    _user_with_email(db_session, "operator@example.com")

    hit = client.post("/api/v1/auth/forgot-password", json={"username_or_email": "operator@example.com"})
    miss = client.post("/api/v1/auth/forgot-password", json={"username_or_email": "nobody@example.com"})

    assert hit.status_code == miss.status_code == 200
    assert hit.json()["message"] == miss.json()["message"]
    assert len(recorder.sent) == 1, "the miss must not have produced a message"


def test_an_inactive_account_gets_no_email(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    """Deactivating somebody has to close the recovery path too, or it is not a deactivation."""
    _configure_mail(monkeypatch)
    recorder = _Recorder()
    monkeypatch.setattr(password_reset, "send_email", recorder)

    user = _user_with_email(db_session, "gone@example.com")
    user.is_active = False
    db_session.commit()

    response = client.post("/api/v1/auth/forgot-password", json={"username_or_email": "gone@example.com"})

    assert response.status_code == 200
    assert response.json()["reset_token"] is None
    assert recorder.sent == []


def test_a_mail_outage_does_not_fail_the_request(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    """The token is stored either way. Telling the caller the provider is down would also
    tell them the identifier matched."""
    _configure_mail(monkeypatch)
    monkeypatch.setattr(password_reset, "send_email", _Recorder(fail=True))

    _user_with_email(db_session, "operator@example.com")

    response = client.post(
        "/api/v1/auth/forgot-password", json={"username_or_email": "operator@example.com"}
    )

    assert response.status_code == 200
    user = db_session.query(User).filter_by(email="operator@example.com").one()
    db_session.refresh(user)
    assert user.reset_token is not None, "the reset must still be usable from the token"


def test_the_send_stays_off_the_request_path() -> None:
    """The endpoint must hand the send to `BackgroundTasks`, never await it.

    This is checked on the signature because there is no way to observe it through
    `TestClient`, which drains background tasks before returning — and the alternative,
    timing the two responses, is exactly the flaky test that would get deleted. The property
    is real: sending inline makes a request for a *matching* identifier take an HTTPS round
    trip to the mail provider longer than one for an unknown identifier, which answers by the
    clock the question the identical message refuses to answer in words.
    """
    import inspect

    from src.modules.authentication import router as auth_router

    annotations = {
        name: parameter.annotation
        for name, parameter in inspect.signature(auth_router.forgot_password).parameters.items()
    }
    assert BackgroundTasks in annotations.values()


def test_an_installation_without_mail_still_completes_the_flow(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    """No credentials is a supported deployment, not a broken one."""
    settings = get_settings()
    monkeypatch.setattr(settings, "hostinger_mail_api_token", "", raising=False)
    monkeypatch.setattr(settings, "hostinger_mailbox_resource_id", "", raising=False)

    _user_with_email(db_session, "operator@example.com")

    forgot = client.post(
        "/api/v1/auth/forgot-password", json={"username_or_email": "operator@example.com"}
    )
    token = forgot.json()["reset_token"]
    assert token, "outside production the token is handed back so the reset can be finished"

    reset = client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "brand-new-pass"}
    )
    assert reset.status_code == 200
