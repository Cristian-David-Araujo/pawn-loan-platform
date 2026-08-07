"""Google Drive upload over plain OAuth 2.0, no Google SDK.

Three HTTPS calls do everything this needs (refresh a token, create a folder, upload a
file), so the SDK would add a dependency tree for nothing.

Why OAuth and not a service account: a service account has **no Drive storage quota of its
own** since Google removed it in 2021. It becomes the owner of whatever it uploads, so the
bytes are charged to a quota of zero and the upload fails with ``storageQuotaExceeded`` even
inside a folder shared with it. It only works against a Shared Drive, which is a paid
Workspace feature. Authorising a normal Google account puts the archives in that account's
own Drive, on its own quota.

The scope is ``drive.file``, which grants access **only to files this application itself
created** — it cannot read the rest of the user's Drive. That is also why the destination
folder is created by us rather than picked from an existing one: a folder we did not create
is invisible under this scope. As a side effect, listing for retention can only ever see our
own archives, so pruning can never delete something else.

``drive.file`` is a non-sensitive scope, so the OAuth application needs no Google
verification. It does need its publishing status set to "In production": while it is in
"Testing", Google expires the refresh token after **seven days** and the schedule stops
working silently. That is what the run history is for.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, BinaryIO
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v3/userinfo"
FILES_ENDPOINT = "https://www.googleapis.com/drive/v3/files"
UPLOAD_ENDPOINT = "https://www.googleapis.com/upload/drive/v3/files"

FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"

# `drive.file` for the archives, `userinfo.email` so the UI can name the connected account.
# Both are non-sensitive: adding `drive` or `drive.readonly` here would make the application
# subject to Google's security assessment, and would let it read the customer's whole Drive.
SCOPES = ("https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/userinfo.email")

REQUEST_TIMEOUT = httpx.Timeout(30.0, read=120.0)

# Uploaded in one request. Export archives of this application are kilobytes to a few
# megabytes; the size is checked before the call so a surprise never lands in memory twice.
MAX_SIMPLE_UPLOAD_BYTES = 64 * 1024 * 1024


class GoogleDriveError(Exception):
    """Any failure talking to Google, with a message fit to show an administrator."""


@dataclass
class DriveCredentials:
    client_id: str
    client_secret: str
    refresh_token: str


@dataclass
class ConnectedAccount:
    refresh_token: str
    email: str | None


@dataclass
class DriveFile:
    id: str
    name: str
    created_time: str | None


def build_authorization_url(client_id: str, redirect_uri: str, state: str) -> str:
    """Consent URL the administrator opens once.

    ``access_type=offline`` is what returns a refresh token at all, and ``prompt=consent``
    forces Google to return it again on a re-authorisation — without it a second run of the
    flow answers with an access token only, and the connection silently keeps using whatever
    token was stored before.
    """
    query = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{AUTHORIZATION_ENDPOINT}?{urlencode(query)}"


def _post_token(payload: dict[str, str]) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.post(TOKEN_ENDPOINT, data=payload)
    except httpx.HTTPError as exc:
        raise GoogleDriveError(f"Could not reach Google to obtain a token: {exc}") from exc

    if response.status_code >= 400:
        raise GoogleDriveError(f"Google rejected the token request: {_describe(response)}")

    return response.json()


def _describe(response: httpx.Response) -> str:
    """Google's own error text, which names the actual problem, kept for the operator."""
    try:
        body = response.json()
    except ValueError:
        return f"HTTP {response.status_code} {response.text[:300]}"

    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            return f"HTTP {response.status_code} {error.get('message') or json.dumps(error)[:300]}"
        description = body.get("error_description") or body.get("error")
        if description:
            return f"HTTP {response.status_code} {description}"

    return f"HTTP {response.status_code} {response.text[:300]}"


def exchange_authorization_code(
    client_id: str, client_secret: str, code: str, redirect_uri: str
) -> ConnectedAccount:
    """Turn the one-time code from the consent redirect into a lasting refresh token."""
    tokens = _post_token(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
    )

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise GoogleDriveError(
            "Google did not return a refresh token. Revoke this application's access in the "
            "Google account and authorise it again."
        )

    return ConnectedAccount(
        refresh_token=refresh_token,
        email=_read_account_email(tokens.get("access_token")),
    )


def _read_account_email(access_token: str | None) -> str | None:
    """Best effort: the connection works without it, the UI is just less informative."""
    if not access_token:
        return None

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.get(USERINFO_ENDPOINT, headers={"Authorization": f"Bearer {access_token}"})
        if response.status_code >= 400:
            return None
        email = response.json().get("email")
        return email if isinstance(email, str) else None
    except (httpx.HTTPError, ValueError):
        return None


def fetch_access_token(credentials: DriveCredentials) -> str:
    """Mint a short lived access token from the stored refresh token.

    A revoked or expired refresh token surfaces here, which is where the operator-facing
    message about re-authorising belongs.
    """
    tokens = _post_token(
        {
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "refresh_token": credentials.refresh_token,
            "grant_type": "refresh_token",
        }
    )

    access_token = tokens.get("access_token")
    if not access_token:
        raise GoogleDriveError(
            "Google did not return an access token. The authorisation may have been revoked; "
            "connect the Google account again."
        )

    return access_token


def _request(
    method: str,
    url: str,
    access_token: str,
    *,
    params: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    content: BinaryIO | bytes | None = None,
    content_type: str | None = None,
) -> httpx.Response:
    response = _send(
        method,
        url,
        access_token,
        params=params,
        json_body=json_body,
        content=content,
        content_type=content_type,
    )

    if response.status_code >= 400:
        raise GoogleDriveError(f"Google Drive rejected the request: {_describe(response)}")

    return response


def _request_optional(
    method: str, url: str, access_token: str, *, params: dict[str, str] | None = None
) -> httpx.Response | None:
    """Like :func:`_request`, but a 404 is an answer rather than a failure."""
    response = _send(method, url, access_token, params=params)

    if response.status_code == 404:
        return None
    if response.status_code >= 400:
        raise GoogleDriveError(f"Google Drive rejected the request: {_describe(response)}")

    return response


def _send(
    method: str,
    url: str,
    access_token: str,
    *,
    params: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    content: BinaryIO | bytes | None = None,
    content_type: str | None = None,
) -> httpx.Response:
    headers = {"Authorization": f"Bearer {access_token}"}
    if content_type:
        headers["Content-Type"] = content_type

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.request(
                method, url, headers=headers, params=params, json=json_body, content=content
            )
    except httpx.HTTPError as exc:
        raise GoogleDriveError(f"Could not reach Google Drive: {exc}") from exc

    return response


def ensure_folder(access_token: str, folder_name: str, folder_id: str | None) -> str:
    """Return the id of the destination folder, creating it the first time.

    A stored id is verified rather than trusted, and a folder that is gone is replaced rather
    than reported: an administrator who deleted or trashed it would otherwise get a 404 on
    every run from then on — a message that reads like a permission problem and a schedule that
    can never recover on its own. Only a 404 falls through to creating one; a transient error
    still fails the run, because treating it as "missing" would scatter duplicate folders.
    """
    if folder_id:
        response = _request_optional(
            "GET",
            f"{FILES_ENDPOINT}/{folder_id}",
            access_token,
            params={"fields": "id,trashed"},
        )
        if response is not None:
            body = response.json()
            if not body.get("trashed"):
                return str(body["id"])

    escaped = folder_name.replace("\\", "\\\\").replace("'", "\\'")
    existing = _request(
        "GET",
        FILES_ENDPOINT,
        access_token,
        params={
            "q": f"mimeType = '{FOLDER_MIME_TYPE}' and name = '{escaped}' and trashed = false",
            "fields": "files(id,name)",
            "pageSize": "10",
        },
    ).json()

    files = existing.get("files") or []
    if files:
        return str(files[0]["id"])

    created = _request(
        "POST",
        FILES_ENDPOINT,
        access_token,
        params={"fields": "id"},
        json_body={"name": folder_name, "mimeType": FOLDER_MIME_TYPE},
    ).json()

    return str(created["id"])


def upload_file(
    access_token: str,
    folder_id: str,
    filename: str,
    stream: BinaryIO,
    size_bytes: int,
) -> DriveFile:
    """Upload the archive with a resumable session, so the bytes are streamed once.

    Resumable rather than multipart: multipart would need the whole archive and its metadata
    assembled in memory as one body, and this runs on a 1 GB droplet alongside PostgreSQL.
    """
    if size_bytes > MAX_SIMPLE_UPLOAD_BYTES:
        raise GoogleDriveError(
            f"The archive is {size_bytes} bytes, larger than this uploader handles "
            f"({MAX_SIMPLE_UPLOAD_BYTES})."
        )

    session = _request(
        "POST",
        UPLOAD_ENDPOINT,
        access_token,
        params={"uploadType": "resumable"},
        json_body={"name": filename, "parents": [folder_id]},
        content_type="application/json; charset=UTF-8",
    )

    session_url = session.headers.get("location")
    if not session_url:
        raise GoogleDriveError("Google Drive did not open an upload session.")

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.put(
                session_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/zip",
                    "Content-Length": str(size_bytes),
                },
                content=stream,
            )
    except httpx.HTTPError as exc:
        raise GoogleDriveError(f"The upload to Google Drive failed: {exc}") from exc

    if response.status_code >= 400:
        raise GoogleDriveError(f"The upload to Google Drive failed: {_describe(response)}")

    body = response.json()
    return DriveFile(id=str(body["id"]), name=str(body.get("name") or filename), created_time=None)


def list_folder_files(access_token: str, folder_id: str) -> list[DriveFile]:
    """Archives in the destination folder, newest first.

    Under ``drive.file`` this only ever returns files this application created, which is what
    makes retention pruning safe: it cannot see, and therefore cannot delete, anything else
    the customer keeps in their Drive.
    """
    files: list[DriveFile] = []
    page_token: str | None = None

    while True:
        params = {
            "q": f"'{folder_id}' in parents and trashed = false",
            "fields": "nextPageToken, files(id,name,createdTime)",
            "orderBy": "createdTime desc",
            "pageSize": "100",
        }
        if page_token:
            params["pageToken"] = page_token

        body = _request("GET", FILES_ENDPOINT, access_token, params=params).json()
        for item in body.get("files") or []:
            files.append(
                DriveFile(id=str(item["id"]), name=str(item.get("name") or ""), created_time=item.get("createdTime"))
            )

        page_token = body.get("nextPageToken")
        if not page_token:
            return files


def delete_file(access_token: str, file_id: str) -> None:
    _request("DELETE", f"{FILES_ENDPOINT}/{file_id}", access_token)
