"""Backs up the SQLite file to GCS and restores it on cold start, so
diagnostics survive a Cloud Run redeploy (the container's own filesystem is
ephemeral and resets on every new revision).

Deliberately NOT a live mounted filesystem (e.g. a Cloud Run GCS FUSE
volume): SQLite's rollback journal needs to seek and overwrite specific
byte offsets, and GCS FUSE's buffered writer only supports sequential
writes - confirmed in production with a live mount:
"BufferedWriteHandler.OutOfOrderError for object: pe_agent.db-journal,
expectedOffset: 512, actualOffset: 0". Backup/restore sidesteps this
entirely: SQLite always operates on a true local file, and GCS is only
ever written to as a whole-file snapshot.

This only protects writes that happened before the most recent backup -
if the container is killed between a write and the next backup_to_gcs()
call, that gap's data is lost. backup_to_gcs() is called (via a background
thread, same pattern as the independent RAGAS/deep-eval passes) after
every mutation that matters: a new diagnostic run, a process deletion, an
edited diagnostics table. Combined with --max-instances=1 (no concurrent
writers racing each other's backups), the loss window in practice is just
"the process restarts mid-write", not "every redeploy".
"""
from __future__ import annotations

import shutil

from app.config.settings import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

_BACKUP_OBJECT_NAME = "pe_agent.db"


def _bucket():
    from google.cloud import storage

    settings = get_settings()
    client = storage.Client()
    return client.bucket(settings.gcs_backup_bucket)


def restore_from_gcs() -> bool:
    """Called once at startup, before init_db() creates any tables. If a
    backup exists in GCS and no local DB file exists yet (a fresh
    container), downloads it so the app resumes from the last backup
    instead of an empty database. No-op if GCS_BACKUP_BUCKET isn't
    configured, or if a local file already exists (never overwrites
    data someone's actively using).
    """
    settings = get_settings()
    if not settings.gcs_backup_bucket:
        return False

    local_path = settings.sqlite_file_path
    if local_path.exists():
        return False

    try:
        blob = _bucket().blob(_BACKUP_OBJECT_NAME)
        if not blob.exists():
            logger.info(f"No existing backup found at gs://{settings.gcs_backup_bucket}/{_BACKUP_OBJECT_NAME}")
            return False
        local_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = local_path.with_suffix(".db.restoring")
        blob.download_to_filename(str(tmp_path))
        shutil.move(str(tmp_path), str(local_path))
        logger.info(f"Restored database from gs://{settings.gcs_backup_bucket}/{_BACKUP_OBJECT_NAME}")
        return True
    except Exception:
        logger.exception("Database restore from GCS failed - starting with a fresh database instead")
        return False


def backup_to_gcs() -> bool:
    """Uploads the current local SQLite file as the new backup, overwriting
    the previous one. Safe to call from a background thread (fire-and-forget
    after a mutation) - failures are logged, never raised, since a failed
    backup must never break the request that triggered it.
    """
    settings = get_settings()
    if not settings.gcs_backup_bucket:
        return False

    local_path = settings.sqlite_file_path
    if not local_path.exists():
        return False

    try:
        blob = _bucket().blob(_BACKUP_OBJECT_NAME)
        blob.upload_from_filename(str(local_path))
        logger.info(f"Backed up database to gs://{settings.gcs_backup_bucket}/{_BACKUP_OBJECT_NAME}")
        return True
    except Exception:
        logger.exception("Database backup to GCS failed")
        return False
