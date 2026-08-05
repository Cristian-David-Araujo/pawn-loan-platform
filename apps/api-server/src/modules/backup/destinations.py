"""Where a scheduled backup is written, and what is pruned once it lands.

Two destinations: a directory on the server and Google Drive. Both answer the same two
questions — store this archive, then drop the copies beyond the retention count — so the
runner never branches on which one is configured.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from shutil import copyfileobj

from src.modules.backup.google_drive import (
    DriveCredentials,
    GoogleDriveError,
    delete_file,
    ensure_folder,
    fetch_access_token,
    list_folder_files,
    upload_file,
)
from src.modules.backup.service import ExportArchive

logger = logging.getLogger(__name__)

LOCAL_DIRECTORY = "local_directory"
GOOGLE_DRIVE = "google_drive"
DESTINATIONS = (LOCAL_DIRECTORY, GOOGLE_DRIVE)

# Only files this application produced are ever deleted by retention. The destination folder
# may hold anything else the operator put there, and a backup job that quietly removes a
# stranger's file is worse than one that keeps too many copies. The captured group is the
# archive's own timestamp, which is what copies are ordered by: the rest of the name is the
# company slug, so ordering by the whole filename would rank copies by company name the day
# an operator edits it.
ARCHIVE_NAME_PATTERN = re.compile(r"^.+-export-(\d{8}-\d{6})\.zip$")


class BackupDestinationError(Exception):
    """The destination is misconfigured or unreachable, with a message for the operator."""


@dataclass
class StoredBackup:
    """Where a copy ended up, and what retention removed on the way."""

    location: str
    pruned: int


@dataclass
class DriveConfiguration:
    credentials: DriveCredentials
    folder_name: str
    folder_id: str | None


def _is_managed_archive(name: str) -> bool:
    return bool(ARCHIVE_NAME_PATTERN.match(name))


def _archive_age_key(name: str) -> str:
    match = ARCHIVE_NAME_PATTERN.match(name)
    return match.group(1) if match else ""


def store_in_directory(archive: ExportArchive, directory: str | None, retention_copies: int) -> StoredBackup:
    if not directory or not directory.strip():
        raise BackupDestinationError("No backup directory is configured.")

    target_directory = Path(directory.strip())

    try:
        target_directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BackupDestinationError(f"The backup directory could not be created: {exc}") from exc

    target = target_directory / archive.filename
    # Written under a temporary name and moved into place, so a run interrupted halfway
    # cannot leave a truncated file that looks like a complete backup.
    staging = target_directory / f".{archive.filename}.partial"

    try:
        with staging.open("wb") as handle:
            copyfileobj(archive.stream, handle)
        staging.replace(target)
    except OSError as exc:
        staging.unlink(missing_ok=True)
        raise BackupDestinationError(f"The backup could not be written: {exc}") from exc

    return StoredBackup(location=str(target), pruned=_prune_directory(target_directory, retention_copies))


def _prune_directory(directory: Path, retention_copies: int) -> int:
    if retention_copies <= 0:
        return 0

    try:
        archives = sorted(
            (path for path in directory.iterdir() if path.is_file() and _is_managed_archive(path.name)),
            key=lambda path: _archive_age_key(path.name),
            reverse=True,
        )
    except OSError as exc:
        # The copy itself succeeded, so a failure to tidy up must not fail the run.
        logger.warning("Could not list the backup directory to apply retention: %s", exc)
        return 0

    pruned = 0
    for path in archives[retention_copies:]:
        try:
            path.unlink()
            pruned += 1
        except OSError as exc:
            logger.warning("Could not remove the expired backup %s: %s", path, exc)

    return pruned


def store_in_google_drive(
    archive: ExportArchive, configuration: DriveConfiguration, retention_copies: int
) -> tuple[StoredBackup, str]:
    """Upload the archive and prune the folder. Returns the copy and the folder id used.

    The folder id comes back because it may have just been created, and storing it saves a
    lookup on every later run.
    """
    try:
        access_token = fetch_access_token(configuration.credentials)
        folder_id = ensure_folder(access_token, configuration.folder_name, configuration.folder_id)
        uploaded = upload_file(
            access_token,
            folder_id,
            archive.filename,
            archive.stream,
            archive.size_bytes,
        )
    except GoogleDriveError as exc:
        raise BackupDestinationError(str(exc)) from exc

    return StoredBackup(location=uploaded.id, pruned=_prune_drive_folder(access_token, folder_id, retention_copies)), folder_id


def _prune_drive_folder(access_token: str, folder_id: str, retention_copies: int) -> int:
    if retention_copies <= 0:
        return 0

    try:
        archives = [item for item in list_folder_files(access_token, folder_id) if _is_managed_archive(item.name)]
    except GoogleDriveError as exc:
        # The upload already succeeded; failing the run over the cleanup would report a
        # backup that exists as a backup that does not.
        logger.warning("Could not list the Drive folder to apply retention: %s", exc)
        return 0

    # `list_folder_files` returns newest first, but the filename carries the archive's own
    # timestamp and is the authority — a copy re-uploaded by hand has a createdTime later than
    # the data inside it.
    archives.sort(key=lambda item: _archive_age_key(item.name), reverse=True)

    pruned = 0
    for item in archives[retention_copies:]:
        try:
            delete_file(access_token, item.id)
            pruned += 1
        except GoogleDriveError as exc:
            logger.warning("Could not remove the expired backup %s from Drive: %s", item.name, exc)

    return pruned


def describe_directory_writability(directory: str | None) -> str:
    """Check a directory can actually be written to, for the destination test.

    Discovering a read-only volume when the first scheduled copy fails at 2am is exactly the
    kind of thing this feature exists to avoid.
    """
    if not directory or not directory.strip():
        raise BackupDestinationError("No backup directory is configured.")

    target_directory = Path(directory.strip())

    try:
        target_directory.mkdir(parents=True, exist_ok=True)
        probe = target_directory / ".backup-write-test"
        probe.write_bytes(b"ok")
        probe.unlink()
    except OSError as exc:
        raise BackupDestinationError(f"The backup directory is not writable: {exc}") from exc

    return str(target_directory)
