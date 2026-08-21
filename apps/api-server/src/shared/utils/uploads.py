"""Validation shared by the protected customer and collateral upload routes."""

from pathlib import Path
import re

from fastapi import HTTPException, UploadFile, status


MAX_COLLATERAL_PHOTO_BYTES = 5 * 1024 * 1024
MAX_IDENTITY_DOCUMENT_BYTES = 10 * 1024 * 1024

_IMAGE_SIGNATURES: tuple[tuple[bytes, str, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
)


def _detected_type(content: bytes, *, allow_pdf: bool) -> tuple[str, str] | None:
    for signature, content_type, extension in _IMAGE_SIGNATURES:
        if content.startswith(signature):
            return content_type, extension

    # WebP is a RIFF container, so both markers must be checked to avoid accepting any RIFF file.
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp", "webp"
    if allow_pdf and content.startswith(b"%PDF-"):
        return "application/pdf", "pdf"
    return None


def _safe_filename(filename: str | None, extension: str) -> str:
    # Browsers normally strip paths, but this endpoint is also called by API clients.
    raw_name = (filename or "upload").replace("\\", "/")
    stem = Path(raw_name).stem
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-") or "upload"
    return f"{stem[:220]}.{extension}"


def read_validated_upload(
    upload: UploadFile,
    *,
    max_bytes: int,
    allow_pdf: bool = False,
) -> tuple[bytes, str, str]:
    """Read a bounded upload and return trusted bytes, content type and a safe file name."""

    content = upload.file.read(max_bytes + 1)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty")
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"The file exceeds the {max_bytes // (1024 * 1024)} MB limit",
        )

    detected = _detected_type(content, allow_pdf=allow_pdf)
    if detected is None:
        expected = "an image or PDF" if allow_pdf else "a JPEG, PNG or WebP image"
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"The file must be {expected}",
        )

    content_type, extension = detected
    return content, content_type, _safe_filename(upload.filename, extension)
