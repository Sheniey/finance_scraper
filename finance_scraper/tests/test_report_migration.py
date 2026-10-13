import json
import sqlite3
from pathlib import Path

import pytest

from api.core.config import APIConfig, settings
from api.services import report_migration
from finance.services.report_store.database import (
    SQLiteReportDatabase,
    create_report_schema,
)
from finance.services.report_store import reports as ReportStore


def _create_legacy_database(
    database_path: Path,
    *,
    report_id: str,
    status: str,
    artifact_path: str | None,
    artifact: bytes | None = None,
) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            '''
            CREATE TABLE api_tokens (
                jti TEXT PRIMARY KEY,
                token_type TEXT NOT NULL
            )
            ''',
        )
        connection.execute(
            'INSERT INTO api_tokens (jti, token_type) VALUES (?, ?)',
            (f'token-{report_id}', 'access'),
        )
        connection.execute(
            '''
            CREATE TABLE api_report_jobs (
                report_id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                ticker TEXT NOT NULL,
                request_json TEXT NOT NULL,
                status TEXT NOT NULL,
                file_name TEXT NOT NULL,
                report_format TEXT NOT NULL,
                artifact_path TEXT,
                error_code TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                started_at INTEGER,
                completed_at INTEGER,
                expires_at INTEGER,
                worker_id TEXT,
                lease_until INTEGER
            )
            ''',
        )
        connection.execute(
            '''
            INSERT INTO api_report_jobs (
                report_id, account_id, ticker, request_json, status,
                file_name, report_format, artifact_path, error_code,
                created_at, updated_at, started_at, completed_at, expires_at,
                worker_id, lease_until
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 100, 110, 105, 110, 3710, NULL, NULL)
            ''',
            (
                report_id,
                'owner-id',
                'AAPL',
                json.dumps({'ticker': 'AAPL'}),
                status,
                'report.pdf',
                'pdf',
                artifact_path,
            ),
        )
    if artifact_path is not None and artifact is not None:
        source_artifact: Path = (
            database_path.parent / 'active_reports' / artifact_path
        )
        source_artifact.parent.mkdir(parents=True, exist_ok=True)
        source_artifact.write_bytes(artifact)


def test_migration_verifies_blobs_and_preserves_token_tables(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy_directory: Path = tmp_path / 'legacy'
    current_database: Path = legacy_directory / 'db.sqlite3'
    second_database: Path = legacy_directory / 'api.sqlite3'
    artifact_relative_path: str = 'rep_legacy/report.pdf'
    artifact_bytes: bytes = b'legacy-pdf-content'
    _create_legacy_database(
        current_database,
        report_id='rep_legacy',
        status='COMPLETED',
        artifact_path=artifact_relative_path,
        artifact=artifact_bytes,
    )
    _create_legacy_database(
        second_database,
        report_id='rep_legacy_failed',
        status='FAILED',
        artifact_path=None,
    )
    temporary_settings: APIConfig = APIConfig(
        api=settings.api.model_copy(
            update={'database_path': current_database},
        ),
    )
    shared_database: SQLiteReportDatabase = SQLiteReportDatabase(
        tmp_path / 'shared' / 'report_store.sqlite3',
    )
    with shared_database.connection() as connection:
        create_report_schema(connection)
    monkeypatch.setattr(report_migration, 'settings', temporary_settings)
    monkeypatch.setattr(ReportStore, 'report_database', shared_database)

    report_migration.migrate_legacy_report_databases()

    stored_report = ReportStore.get_report_job(
        'rep_legacy',
        account_id='owner-id',
        include_artifact=True,
    )
    stored_failed_report = ReportStore.get_report_job(
        'rep_legacy_failed',
        account_id='owner-id',
    )
    assert stored_report is not None
    assert stored_report.artifact == artifact_bytes
    assert stored_report.is_personalized
    assert stored_failed_report is not None
    assert stored_failed_report.status == 'FAILED'
    assert not (
        legacy_directory / 'active_reports' / artifact_relative_path
    ).exists()

    for database_path in (current_database, second_database):
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'",
                )
            }
            assert 'api_report_jobs' not in tables
            assert 'api_tokens' in tables
            assert connection.execute(
                'SELECT COUNT(*) FROM api_tokens',
            ).fetchone()[0] == 1

    report_migration.migrate_legacy_report_databases()
    assert ReportStore.get_report_job(
        'rep_legacy',
        account_id='owner-id',
        include_artifact=True,
    ) == stored_report
