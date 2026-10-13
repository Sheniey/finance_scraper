import json
import logging
import mimetypes
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from api.core.config import settings
from finance.services.report_store import reports as ReportStore


logger: logging.Logger = logging.getLogger(__name__)
_REPORT_STATUSES: frozenset[str] = frozenset(
    {'PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED'},
)


def _legacy_database_paths() -> tuple[Path, ...]:
    current_database: Path = settings.api.database_path.resolve()
    previous_database: Path = current_database.with_name('api.sqlite3')
    return tuple(dict.fromkeys((current_database, previous_database)))


def _resolve_legacy_artifact(
    database_path: Path,
    artifact_path: str | None,
) -> tuple[Path | None, bytes | None]:
    if not artifact_path:
        return None, None

    artifact_root: Path = (database_path.parent / 'active_reports').resolve()
    source_path: Path = Path(artifact_path)
    resolved_path: Path = (
        source_path.resolve()
        if source_path.is_absolute()
        else (artifact_root / source_path).resolve()
    )
    try:
        resolved_path.relative_to(artifact_root)
    except ValueError as e:
        raise ValueError(
            f'Legacy report artifact escapes its storage directory: {artifact_path!r}',
        ) from e
    if not resolved_path.is_file():
        return resolved_path, None
    return resolved_path, resolved_path.read_bytes()


def _request_data(value: Any, report_id: str) -> dict[str, Any]:
    if not isinstance(value, str):
        raise ValueError(f'Legacy report {report_id} has no request JSON')
    decoded: Any = json.loads(value)
    if not isinstance(decoded, dict):
        raise ValueError(
            f'Legacy report {report_id} request must be a JSON object',
        )
    return decoded


def _optional_int(row: sqlite3.Row, field: str) -> int | None:
    value: Any = row[field] if field in row.keys() else None
    return int(value) if value is not None else None


def _migrate_legacy_database(database_path: Path) -> None:
    source_database: str = database_path.resolve().as_posix()
    if ReportStore.was_legacy_database_migrated(source_database):
        return

    read_only_uri: str = f'{database_path.resolve().as_uri()}?mode=ro'
    with closing(sqlite3.connect(read_only_uri, uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        table: sqlite3.Row | None = connection.execute(
            '''
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'api_report_jobs'
            LIMIT 1
            ''',
        ).fetchone()
        if table is None:
            ReportStore.mark_legacy_database_migrated(source_database)
            return
        rows: list[sqlite3.Row] = connection.execute(
            'SELECT * FROM api_report_jobs ORDER BY created_at, report_id',
        ).fetchall()

    artifacts_to_remove: dict[Path, bytes] = {}
    for row in rows:
        report_id: str = str(row['report_id'])
        account_id: str = str(row['account_id'])
        request: dict[str, Any] = _request_data(
            row['request_json'],
            report_id,
        )
        status: str = str(row['status']).upper()
        if status not in _REPORT_STATUSES:
            raise ValueError(
                f'Legacy report {report_id} has an unknown status {status!r}',
            )
        filename: str = str(row['file_name'])
        report_format: str = str(row['report_format']).lower()
        artifact_path_value: str | None = (
            str(row['artifact_path'])
            if 'artifact_path' in row.keys()
            and row['artifact_path'] is not None
            else None
        )
        source_path, artifact = _resolve_legacy_artifact(
            database_path,
            artifact_path_value,
        )
        if status == 'COMPLETED' and not artifact:
            previously_stored = ReportStore.get_report_job(
                report_id,
                account_id=account_id,
                include_artifact=True,
            )
            if (
                previously_stored is not None
                and previously_stored.status == 'COMPLETED'
                and previously_stored.artifact
            ):
                artifact = previously_stored.artifact
        if source_path is not None and artifact is not None:
            existing_artifact: bytes | None = artifacts_to_remove.get(source_path)
            if existing_artifact is not None and existing_artifact != artifact:
                raise RuntimeError(
                    f'Legacy report artifact changed during migration: {source_path}',
                )
            artifacts_to_remove[source_path] = artifact

        created_at: int = int(row['created_at'])
        updated_at: int = int(row['updated_at'])
        started_at: int | None = _optional_int(row, 'started_at')
        completed_at: int | None = _optional_int(row, 'completed_at')
        expires_at: int | None = _optional_int(row, 'expires_at')
        if (
            status in {'COMPLETED', 'FAILED'}
            and expires_at is None
            and completed_at is not None
        ):
            expires_at = completed_at + settings.api.report_retention_seconds

        ReportStore.import_legacy_report_job(
            report_id=report_id,
            account_id=account_id,
            resource=str(row['ticker']),
            request=request,
            status=status,
            filename=filename,
            report_format=report_format,
            content_type=(
                mimetypes.guess_type(filename)[0]
                or 'application/octet-stream'
            ),
            metadata={'migration_source': database_path.name},
            artifact=artifact,
            error_code=(
                str(row['error_code'])
                if 'error_code' in row.keys()
                and row['error_code'] is not None
                else None
            ),
            created_at=created_at,
            updated_at=updated_at,
            started_at=started_at,
            completed_at=completed_at,
            expires_at=expires_at,
        )
        stored_job = ReportStore.get_report_job(
            report_id,
            account_id=account_id,
            include_artifact=True,
        )
        if stored_job is None:
            raise RuntimeError(
                f'Could not verify migrated report {report_id}',
            )
        expected_status: str = status
        if status == 'IN_PROGRESS':
            expected_status = 'PENDING'
        if status == 'COMPLETED' and not artifact:
            expected_status = 'FAILED'
        if (
            stored_job.status != expected_status
            or stored_job.artifact != artifact
            or stored_job.account_id != account_id
            or stored_job.resource != str(row['ticker'])
            or stored_job.request != request
            or stored_job.filename != filename
            or stored_job.report_format != report_format
            or not stored_job.is_personalized
        ):
            raise RuntimeError(
                f'Migrated report {report_id} did not match its source row',
            )

    for artifact_path, expected_content in artifacts_to_remove.items():
        if not artifact_path.is_file():
            continue
        if artifact_path.read_bytes() != expected_content:
            raise RuntimeError(
                f'Legacy report artifact changed before cleanup: {artifact_path}',
            )
        artifact_path.unlink()

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute('BEGIN IMMEDIATE')
        connection.execute('DROP TABLE api_report_jobs')
        connection.commit()
    ReportStore.mark_legacy_database_migrated(source_database)
    logger.info(
        'Migrated %s legacy report jobs from %s',
        len(rows),
        database_path,
    )


def migrate_legacy_report_databases() -> None:
    ReportStore.initialize_report_store()
    for database_path in _legacy_database_paths():
        if database_path.is_file():
            _migrate_legacy_database(database_path)
