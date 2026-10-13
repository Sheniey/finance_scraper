import json
import mimetypes
import time
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from finance.config import IS_DEV
from finance.services.report_store.database import report_database
from finance.services.report_store.models import StoredReportJob


REPORT_RETENTION_SECONDS: int = 3600


def _json_object(value: str, field: str) -> dict[str, Any]:
    decoded: Any = json.loads(value)
    if not isinstance(decoded, dict):
        raise ValueError(f'Stored report {field} must be a JSON object')
    return decoded


def _job_from_row(row: Mapping[str, Any]) -> StoredReportJob:
    artifact_value: bytes | None = (
        bytes(row['artifact'])
        if row['artifact'] is not None
        else None
    )
    return StoredReportJob(
        report_id=str(row['report_id']),
        account_id=str(row['account_id']),
        resource=str(row['resource']),
        request=_json_object(str(row['request_json']), 'request'),
        status=str(row['status']),
        filename=str(row['filename']),
        report_format=str(row['report_format']),
        content_type=str(row['content_type']),
        metadata=_json_object(str(row['metadata_json']), 'metadata'),
        artifact=artifact_value,
        cache_key=(
            str(row['cache_key'])
            if row['cache_key'] is not None
            else None
        ),
        is_personalized=bool(row['is_personalized']),
        source=str(row['source']),
        error_code=(
            str(row['error_code'])
            if row['error_code'] is not None
            else None
        ),
        created_at=int(row['created_at']),
        updated_at=int(row['updated_at']),
        started_at=(
            int(row['started_at'])
            if row['started_at'] is not None
            else None
        ),
        completed_at=(
            int(row['completed_at'])
            if row['completed_at'] is not None
            else None
        ),
        expires_at=(
            int(row['expires_at'])
            if row['expires_at'] is not None
            else None
        ),
        worker_id=(
            str(row['worker_id'])
            if row['worker_id'] is not None
            else None
        ),
        lease_until=(
            int(row['lease_until'])
            if row['lease_until'] is not None
            else None
        ),
    )


def _serialize_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(',', ':'),
        sort_keys=True,
    )


def _report_select(*, include_artifact: bool = False) -> str:
    artifact_column: str = 'artifact' if include_artifact else 'NULL AS artifact'
    return f'''
        SELECT
            report_id, account_id, resource, request_json, status,
            filename, report_format, content_type, metadata_json,
            {artifact_column}, cache_key, is_personalized, source,
            error_code, created_at, updated_at, started_at, completed_at,
            expires_at, worker_id, lease_until
        FROM report_jobs
    '''


def initialize_report_store() -> None:
    report_database.initialize()


def create_report_job(
    *,
    account_id: str,
    resource: str,
    request: Mapping[str, Any],
    filename: str,
    report_format: str,
    content_type: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    cache_key: str | None = None,
    is_personalized: bool = False,
    source: str = 'api',
    now: int | None = None,
    report_id: str | None = None,
) -> StoredReportJob:
    initialize_report_store()
    created_at: int = now if now is not None else int(time.time())
    resolved_report_id: str = report_id or f'rep_{uuid4().hex}'
    resolved_content_type: str = (
        content_type
        or mimetypes.guess_type(filename)[0]
        or 'application/octet-stream'
    )
    with report_database.transaction() as connection:
        connection.execute(
            '''
            INSERT INTO report_jobs (
                report_id, account_id, resource, request_json, status,
                filename, report_format, content_type, metadata_json,
                cache_key, is_personalized, source, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                resolved_report_id,
                account_id,
                resource,
                _serialize_json(request),
                'PENDING',
                filename,
                report_format,
                resolved_content_type,
                _serialize_json(metadata or {}),
                cache_key,
                int(is_personalized),
                source,
                created_at,
                created_at,
            ),
        )
    job: StoredReportJob | None = get_report_job(
        resolved_report_id,
        account_id=account_id,
    )
    if job is None:
        raise RuntimeError('Created report job could not be reloaded')
    return job


def get_report_job(
    report_id: str,
    *,
    account_id: str | None,
    include_artifact: bool = False,
) -> StoredReportJob | None:
    initialize_report_store()
    query: str = _report_select(include_artifact=include_artifact)
    if account_id is None:
        if include_artifact:
            return None
        query += '''
            WHERE report_id = ? AND is_personalized = 0
            LIMIT 1
        '''
        parameters: tuple[str, ...] = (report_id,)
    else:
        query += '''
            WHERE report_id = ? AND account_id = ?
            LIMIT 1
        '''
        parameters = (report_id, account_id)
    with report_database.connection() as connection:
        row: Mapping[str, Any] | None = connection.execute(
            query,
            parameters,
        ).fetchone()
    return _job_from_row(row) if row is not None else None


def list_report_jobs(
    *,
    account_id: str | None,
    source: str | None = None,
) -> list[StoredReportJob]:
    initialize_report_store()
    query: str = _report_select()
    conditions: list[str] = []
    parameters: list[str] = []
    if account_id is None:
        conditions.append('is_personalized = 0')
    else:
        conditions.append('account_id = ?')
        parameters.append(account_id)
    if source is not None:
        conditions.append('source = ?')
        parameters.append(source)
    query += f'WHERE {" AND ".join(conditions)} ORDER BY created_at DESC, report_id DESC'
    with report_database.connection() as connection:
        rows: list[Mapping[str, Any]] = connection.execute(
            query,
            parameters,
        ).fetchall()
    return [_job_from_row(row) for row in rows]


def claim_next_report_job(
    worker_id: str,
    *,
    now: int | None = None,
    lease_seconds: int = 120,
) -> StoredReportJob | None:
    initialize_report_store()
    claimed_at: int = now if now is not None else int(time.time())
    lease_until: int = claimed_at + lease_seconds
    with report_database.transaction() as connection:
        row: Mapping[str, Any] | None = connection.execute(
            '''
            SELECT report_id
            FROM report_jobs
            WHERE source = 'api'
                AND (
                    status = 'PENDING'
                    OR (status = 'IN_PROGRESS' AND lease_until < ?)
                )
            ORDER BY created_at, report_id
            LIMIT 1
            ''',
            (claimed_at,),
        ).fetchone()
        if row is None:
            return None
        report_id: str = str(row['report_id'])
        updated = connection.execute(
            '''
            UPDATE report_jobs
            SET status = 'IN_PROGRESS',
                updated_at = ?,
                started_at = COALESCE(started_at, ?),
                worker_id = ?,
                lease_until = ?
            WHERE report_id = ?
                AND (
                    status = 'PENDING'
                    OR (status = 'IN_PROGRESS' AND lease_until < ?)
                )
            ''',
            (
                claimed_at,
                claimed_at,
                worker_id,
                lease_until,
                report_id,
                claimed_at,
            ),
        )
        if updated.rowcount != 1:
            return None
        claimed_row: Mapping[str, Any] | None = connection.execute(
            _report_select() + 'WHERE report_id = ?',
            (report_id,),
        ).fetchone()
    if claimed_row is None:
        raise RuntimeError('Claimed report job could not be reloaded')
    return _job_from_row(claimed_row)


def renew_report_lease(
    report_id: str,
    worker_id: str,
    *,
    now: int | None = None,
    lease_seconds: int = 120,
) -> bool:
    initialize_report_store()
    renewed_at: int = now if now is not None else int(time.time())
    with report_database.transaction() as connection:
        result = connection.execute(
            '''
            UPDATE report_jobs
            SET updated_at = ?, lease_until = ?
            WHERE report_id = ?
                AND status = 'IN_PROGRESS'
                AND worker_id = ?
            ''',
            (
                renewed_at,
                renewed_at + lease_seconds,
                report_id,
                worker_id,
            ),
        )
    return result.rowcount == 1


def complete_report_job(
    report_id: str,
    worker_id: str,
    artifact: bytes,
    *,
    content_type: str,
    metadata: Mapping[str, Any] | None = None,
    cache_key: str | None = None,
    is_personalized: bool,
    now: int | None = None,
    ttl_seconds: int = REPORT_RETENTION_SECONDS,
) -> bool:
    if not artifact:
        raise ValueError('Report artifacts cannot be empty')
    if ttl_seconds <= 0:
        raise ValueError('Report retention must be positive')
    initialize_report_store()
    completed_at: int = now if now is not None else int(time.time())
    metadata_json: str = _serialize_json(metadata or {})
    with report_database.transaction() as connection:
        result = connection.execute(
            '''
            UPDATE report_jobs
            SET status = 'COMPLETED',
                artifact = ?,
                content_type = ?,
                metadata_json = ?,
                cache_key = ?,
                is_personalized = ?,
                error_code = NULL,
                updated_at = ?,
                completed_at = ?,
                expires_at = ?,
                worker_id = NULL,
                lease_until = NULL
            WHERE report_id = ?
                AND status = 'IN_PROGRESS'
                AND worker_id = ?
            ''',
            (
                artifact,
                content_type,
                metadata_json,
                cache_key,
                int(is_personalized),
                completed_at,
                completed_at,
                completed_at + ttl_seconds,
                report_id,
                worker_id,
            ),
        )
    return result.rowcount == 1


def update_report_retention(ttl_seconds: int) -> int:
    if ttl_seconds <= 0:
        raise ValueError('Report retention must be positive')
    initialize_report_store()
    with report_database.transaction() as connection:
        result = connection.execute(
            '''
            UPDATE report_jobs
            SET expires_at = completed_at + ?
            WHERE completed_at IS NOT NULL
                AND status IN ('COMPLETED', 'FAILED')
            ''',
            (ttl_seconds,),
        )
    return result.rowcount


def fail_report_job(
    report_id: str,
    worker_id: str,
    error_code: str,
    *,
    is_personalized: bool = False,
    now: int | None = None,
    ttl_seconds: int = REPORT_RETENTION_SECONDS,
) -> bool:
    if ttl_seconds <= 0:
        raise ValueError('Report retention must be positive')
    initialize_report_store()
    completed_at: int = now if now is not None else int(time.time())
    with report_database.transaction() as connection:
        result = connection.execute(
            '''
            UPDATE report_jobs
            SET status = 'FAILED',
                error_code = ?,
                is_personalized = ?,
                updated_at = ?,
                completed_at = ?,
                expires_at = ?,
                worker_id = NULL,
                lease_until = NULL
            WHERE report_id = ?
                AND status = 'IN_PROGRESS'
                AND worker_id = ?
            ''',
            (
                error_code,
                int(is_personalized),
                completed_at,
                completed_at,
                completed_at + ttl_seconds,
                report_id,
                worker_id,
            ),
        )
    return result.rowcount == 1


def create_cli_artifact(
    *,
    account_id: str,
    resource: str,
    filename: str,
    report_format: str,
    content_type: str,
    artifact: bytes,
    request: Mapping[str, Any],
    metadata: Mapping[str, Any],
    is_personalized: bool,
    cache_key: str | None,
    now: int | None = None,
    ttl_seconds: int = REPORT_RETENTION_SECONDS,
) -> str:
    if not artifact:
        raise ValueError('Report artifacts cannot be empty')
    if ttl_seconds <= 0:
        raise ValueError('Report retention must be positive')
    initialize_report_store()
    completed_at: int = now if now is not None else int(time.time())
    if not IS_DEV:
        cleanup_expired_report_jobs(now=completed_at)
    report_id: str = f'rep_{uuid4().hex}'
    with report_database.transaction() as connection:
        connection.execute(
            '''
            INSERT INTO report_jobs (
                report_id, account_id, resource, request_json, status,
                filename, report_format, content_type, metadata_json,
                artifact, cache_key, is_personalized, source,
                created_at, updated_at, started_at, completed_at, expires_at
            )
            VALUES (?, ?, ?, ?, 'COMPLETED', ?, ?, ?, ?, ?, ?, ?, 'cli', ?, ?, ?, ?, ?)
            ''',
            (
                report_id,
                account_id,
                resource,
                _serialize_json(request),
                filename,
                report_format,
                content_type,
                _serialize_json(metadata),
                artifact,
                cache_key,
                int(is_personalized),
                completed_at,
                completed_at,
                completed_at,
                completed_at,
                completed_at + ttl_seconds,
            ),
        )
    return report_id


def delete_report_job(
    report_id: str,
    *,
    account_id: str | None,
) -> bool:
    initialize_report_store()
    with report_database.transaction() as connection:
        if account_id is None:
            result = connection.execute(
                'DELETE FROM report_jobs WHERE report_id = ?',
                (report_id,),
            )
        else:
            result = connection.execute(
                '''
                DELETE FROM report_jobs
                WHERE report_id = ? AND account_id = ?
                ''',
                (report_id, account_id),
            )
    return result.rowcount == 1


def delete_report_jobs(
    *,
    account_id: str | None,
) -> int:
    initialize_report_store()
    with report_database.transaction() as connection:
        if account_id is None:
            result = connection.execute('DELETE FROM report_jobs')
        else:
            result = connection.execute(
                'DELETE FROM report_jobs WHERE account_id = ?',
                (account_id,),
            )
    return result.rowcount


def cleanup_expired_report_jobs(*, now: int | None = None) -> int:
    initialize_report_store()
    cleanup_at: int = now if now is not None else int(time.time())
    with report_database.transaction() as connection:
        result = connection.execute(
            '''
            DELETE FROM report_jobs
            WHERE status IN ('COMPLETED', 'FAILED')
                AND expires_at IS NOT NULL
                AND expires_at <= ?
            ''',
            (cleanup_at,),
        )
    report_database.checkpoint()
    return result.rowcount


def was_legacy_database_migrated(source_database: str) -> bool:
    initialize_report_store()
    with report_database.connection() as connection:
        row: Mapping[str, Any] | None = connection.execute(
            '''
            SELECT 1
            FROM report_store_migrations
            WHERE source_database = ?
            LIMIT 1
            ''',
            (source_database,),
        ).fetchone()
    return row is not None


def import_legacy_report_job(
    *,
    report_id: str,
    account_id: str,
    resource: str,
    request: Mapping[str, Any],
    status: str,
    filename: str,
    report_format: str,
    content_type: str,
    metadata: Mapping[str, Any],
    artifact: bytes | None,
    error_code: str | None,
    created_at: int,
    updated_at: int,
    started_at: int | None,
    completed_at: int | None,
    expires_at: int | None,
) -> None:
    initialize_report_store()
    normalized_status: str = status
    normalized_started_at: int | None = started_at
    if status == 'IN_PROGRESS':
        normalized_status = 'PENDING'
        normalized_started_at = None
    if normalized_status == 'COMPLETED' and not artifact:
        normalized_status = 'FAILED'
        error_code = 'LEGACY_ARTIFACT_MISSING'
    with report_database.transaction() as connection:
        connection.execute(
            '''
            INSERT INTO report_jobs (
                report_id, account_id, resource, request_json, status,
                filename, report_format, content_type, metadata_json,
                artifact, is_personalized, source, error_code,
                created_at, updated_at, started_at, completed_at, expires_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'api', ?, ?, ?, ?, ?, ?)
            ON CONFLICT(report_id) DO NOTHING
            ''',
            (
                report_id,
                account_id,
                resource,
                _serialize_json(request),
                normalized_status,
                filename,
                report_format,
                content_type,
                _serialize_json(metadata),
                artifact,
                error_code,
                created_at,
                updated_at,
                normalized_started_at,
                completed_at,
                expires_at,
            ),
        )


def mark_legacy_database_migrated(
    source_database: str,
    *,
    now: int | None = None,
) -> None:
    initialize_report_store()
    migrated_at: int = now if now is not None else int(time.time())
    with report_database.transaction() as connection:
        connection.execute(
            '''
            INSERT INTO report_store_migrations (source_database, completed_at)
            VALUES (?, ?)
            ON CONFLICT(source_database) DO NOTHING
            ''',
            (source_database, migrated_at),
        )
