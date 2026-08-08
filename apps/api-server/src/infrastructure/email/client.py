"""Sending mail through the Hostinger Mail API.

The transport only. What a given message *says* lives beside the flow that sends it — see
`password_reset.py` — so a second kind of mail does not have to reach into this file.

Two things here are decisions rather than mechanics:

**It raises.** Every failure — missing configuration, a rejected token, a network timeout —
comes back as an exception. The first version logged and returned, which meant a password
reset that never arrived looked exactly like one that did: the operator was told to check
their inbox and nothing was ever coming. A caller that genuinely wants to continue on
failure has to say so.

**The sender is the mailbox, not a setting.** `V1SendRequest` has no `from` field: the
address is whichever mailbox `HOSTINGER_MAILBOX_RESOURCE_ID` names, and the token must be
authorised for it. Only the display name is ours to choose. An earlier `MAIL_FROM_ADDRESS`
setting looked like it selected the sender and did nothing at all.
"""

from __future__ import annotations

import logging

import hostinger_mail_api
from hostinger_mail_api.rest import ApiException

from src.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

# The API is a single HTTPS round trip. Without a ceiling a stalled connection would pin the
# background worker that is running the send for as long as the socket stays open.
REQUEST_TIMEOUT_SECONDS = 15.0


class EmailNotConfigured(RuntimeError):
    """No mail credentials on this installation, so nothing can be delivered."""


class EmailSendFailed(RuntimeError):
    """The API was reached and refused, or could not be reached at all."""


def email_is_configured() -> bool:
    """Whether this installation can deliver mail at all.

    Deployments without credentials are a supported state, not a broken one: the password
    reset flow falls back to handing the token to the operator, which is what it did before
    any mailer existed.
    """
    settings = get_settings()
    return bool(settings.hostinger_mail_api_token and settings.hostinger_mailbox_resource_id)


def send_email(*, to: str, subject: str, html: str, text: str) -> None:
    """Sends one message. Raises on any failure.

    `text` is not optional. A mail client that cannot render HTML, and every spam filter that
    scores multipart messages, want a plain-text alternative — and the reset link has to
    survive in it, because that is the whole point of the message.
    """
    settings = get_settings()

    if not email_is_configured():
        raise EmailNotConfigured(
            "HOSTINGER_MAIL_API_TOKEN and HOSTINGER_MAILBOX_RESOURCE_ID must both be set"
        )

    configuration = hostinger_mail_api.Configuration(access_token=settings.hostinger_mail_api_token)

    try:
        with hostinger_mail_api.ApiClient(configuration) as api_client:
            hostinger_mail_api.SendApi(api_client).send_email(
                mailbox_resource_id=settings.hostinger_mailbox_resource_id,
                v1_send_request=hostinger_mail_api.V1SendRequest(
                    to=[to],
                    display_name=settings.mail_from_name,
                    subject=subject,
                    html=html,
                    text=text,
                ),
                _request_timeout=REQUEST_TIMEOUT_SECONDS,
            )
    except ApiException as exc:
        # 403 here is almost always the mailbox id rather than the token: the id must be the
        # `resourceId` of a mailbox the token is authorised for (AccountApi.get_current_account
        # lists them), and a plausible-looking placeholder such as "me" is refused the same way
        # a revoked token would be. Saying so beats another round of guessing.
        raise EmailSendFailed(
            f"Hostinger refused the message (status {exc.status}): {exc.body}"
        ) from exc
    except Exception as exc:  # noqa: BLE001 - the SDK raises urllib3 errors that share no base
        raise EmailSendFailed(f"Could not reach the Hostinger Mail API: {exc}") from exc
