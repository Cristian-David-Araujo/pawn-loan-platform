"""The password recovery message.

Kept beside the transport rather than inside it so a second kind of mail — a receipt, an
arrears notice — does not have to edit the sender to add itself.

The link points at the **web client**, not the API: `FRONTEND_URL` plus the route
`ResetPasswordView` is mounted on. Getting that wrong sends the customer to a JSON endpoint.
"""

from __future__ import annotations

import logging

from src.infrastructure.config.settings import get_settings
from src.infrastructure.email.client import EmailNotConfigured, EmailSendFailed, send_email

logger = logging.getLogger(__name__)

# Spanish first: it is the language the staff work in (see PRODUCT.md), so it is what an
# unrecognised or absent locale gets.
_SUBJECT = {
    "es": "Recupera tu contraseña",
    "en": "Reset your password",
}

_EXPIRY_MINUTES = 15


def _reset_link(token: str) -> str:
    base = get_settings().frontend_url.rstrip("/")
    return f"{base}/reset-password?token={token}"


def normalise_locale(*candidates: str | None) -> str:
    """Picks 'es' or 'en' from the first candidate that names either.

    Candidates are tried in order: what the client explicitly asked for, then its
    `Accept-Language`. The header is parsed by its first tag's primary subtag rather than by
    searching the whole string — `"es" in "fr-ES,fr;q=0.9"` is true and would have sent a
    French speaker Spanish.
    """
    for candidate in candidates:
        if not candidate:
            continue
        first_tag = candidate.split(",")[0].split(";")[0].strip().lower()
        primary = first_tag.split("-")[0]
        if primary in _SUBJECT:
            return primary
    return "es"


def build_message(token: str, locale: str) -> tuple[str, str, str]:
    """Returns (subject, html, text) for the given token.

    An unrecognised locale gets Spanish, subject included. The body already fell back that
    way; reading the subject out of the map directly would have raised on the same input the
    body handled, so a caller that skipped `normalise_locale` failed on the line after the
    one that had just absorbed it.
    """
    link = _reset_link(token)
    app = get_settings().mail_from_name
    locale = locale if locale in _SUBJECT else "es"

    if locale == "en":
        html = f"""\
<!doctype html>
<html lang="en">
  <body style="margin:0;padding:24px;background:#faf9f7;font-family:Helvetica,Arial,sans-serif;color:#1c1a17;">
    <div style="max-width:520px;margin:0 auto;background:#ffffff;border:1px solid #e4e2dd;border-radius:10px;padding:32px;">
      <h1 style="margin:0 0 16px;font-size:20px;font-weight:700;">Reset your password</h1>
      <p style="margin:0 0 16px;line-height:1.6;">
        Someone asked to reset the password for your {app} account. If it was you, use the
        button below. The link works once and expires in {_EXPIRY_MINUTES} minutes.
      </p>
      <p style="margin:0 0 24px;">
        <a href="{link}" style="display:inline-block;background:#232019;color:#faf9f7;text-decoration:none;padding:12px 20px;border-radius:6px;font-weight:600;">Reset password</a>
      </p>
      <p style="margin:0 0 8px;line-height:1.6;color:#6b655c;font-size:13px;">
        If the button does not work, paste this into your browser:
      </p>
      <p style="margin:0 0 24px;word-break:break-all;font-size:13px;color:#0d5c53;">{link}</p>
      <p style="margin:0;line-height:1.6;color:#6b655c;font-size:13px;">
        If you did not ask for this, nothing has changed and you can ignore this message.
      </p>
    </div>
  </body>
</html>"""
        text = (
            f"Someone asked to reset the password for your {app} account.\n\n"
            f"Open this link to choose a new one:\n{link}\n\n"
            f"The link works once and expires in {_EXPIRY_MINUTES} minutes.\n"
            "If you did not ask for this, nothing has changed and you can ignore this message.\n"
        )
    else:
        html = f"""\
<!doctype html>
<html lang="es">
  <body style="margin:0;padding:24px;background:#faf9f7;font-family:Helvetica,Arial,sans-serif;color:#1c1a17;">
    <div style="max-width:520px;margin:0 auto;background:#ffffff;border:1px solid #e4e2dd;border-radius:10px;padding:32px;">
      <h1 style="margin:0 0 16px;font-size:20px;font-weight:700;">Recupera tu contraseña</h1>
      <p style="margin:0 0 16px;line-height:1.6;">
        Alguien pidió restablecer la contraseña de tu cuenta de {app}. Si fuiste tú, usa el
        botón de abajo. El enlace sirve una sola vez y vence en {_EXPIRY_MINUTES} minutos.
      </p>
      <p style="margin:0 0 24px;">
        <a href="{link}" style="display:inline-block;background:#232019;color:#faf9f7;text-decoration:none;padding:12px 20px;border-radius:6px;font-weight:600;">Restablecer contraseña</a>
      </p>
      <p style="margin:0 0 8px;line-height:1.6;color:#6b655c;font-size:13px;">
        Si el botón no funciona, pega esto en tu navegador:
      </p>
      <p style="margin:0 0 24px;word-break:break-all;font-size:13px;color:#0d5c53;">{link}</p>
      <p style="margin:0;line-height:1.6;color:#6b655c;font-size:13px;">
        Si no lo pediste, no ha cambiado nada y puedes ignorar este mensaje.
      </p>
    </div>
  </body>
</html>"""
        text = (
            f"Alguien pidió restablecer la contraseña de tu cuenta de {app}.\n\n"
            f"Abre este enlace para elegir una nueva:\n{link}\n\n"
            f"El enlace sirve una sola vez y vence en {_EXPIRY_MINUTES} minutos.\n"
            "Si no lo pediste, no ha cambiado nada y puedes ignorar este mensaje.\n"
        )

    return _SUBJECT[locale], html, text


def send_password_reset_email(to_email: str, token: str, locale: str = "es") -> None:
    """Delivers the reset link.

    Runs **after** the response has gone out (the endpoint hands it to `BackgroundTasks`), so
    raising here cannot reach the caller. That is exactly why it must not raise: the failure
    has to end up somewhere a human will find it, which is the log.

    It is also why the endpoint must not await this. The send only happens for an address
    that exists, and a request that waits on it answers measurably slower than one for an
    unknown identifier — which is the enumeration answer the whole endpoint withholds.
    """
    subject, html, text = build_message(token, locale)

    try:
        send_email(to=to_email, subject=subject, html=html, text=text)
    except EmailNotConfigured:
        # Not a fault. An installation with no mail credentials hands the token back to the
        # operator instead, so this is the expected path there and does not deserve a stack
        # trace on every recovery request.
        logger.info(
            "No mail credentials on this installation; the password reset token for %s was "
            "not emailed and must be handed over from the API response.",
            to_email,
        )
    except EmailSendFailed as exc:
        logger.error("Password reset email to %s was not delivered: %s", to_email, exc)
    except Exception:  # noqa: BLE001 - a background task that raises dies silently
        logger.exception("Unexpected failure sending the password reset email to %s", to_email)
    else:
        logger.info("Password reset email sent to %s", to_email)
