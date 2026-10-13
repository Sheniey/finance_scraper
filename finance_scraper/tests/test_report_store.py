from pathlib import Path

from finance.services.report_store.cache import SQLiteCache
from finance.services.report_store.database import (
    SQLiteReportDatabase,
    create_report_schema,
)
from finance.services.report_store import reports as ReportStore


def test_sqlite_cache_respects_ttl(tmp_path: Path) -> None:
    database: SQLiteReportDatabase = SQLiteReportDatabase(
        tmp_path / 'report_store.sqlite3',
    )
    cache: SQLiteCache = SQLiteCache(database)

    cache.set('test', 'entry', b'value', ttl_seconds=5, now=100)

    assert cache.get('test', 'entry', now=104) == b'value'
    assert cache.get('test', 'entry', now=105) is None


def test_report_artifacts_are_owner_private_and_expire(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database: SQLiteReportDatabase = SQLiteReportDatabase(
        tmp_path / 'report_store.sqlite3',
    )
    with database.connection() as connection:
        create_report_schema(connection)
    monkeypatch.setattr(ReportStore, 'report_database', database)
    job = ReportStore.create_report_job(
        account_id='owner-a',
        resource='AAPL.US',
        request={'ticker': 'AAPL.US'},
        filename='report.pdf',
        report_format='pdf',
        now=100,
        report_id='rep_private',
    )
    assert job.status == 'PENDING'

    claimed_job = ReportStore.claim_next_report_job(
        'worker',
        now=101,
        lease_seconds=30,
    )
    assert claimed_job is not None
    assert claimed_job.report_id == job.report_id
    assert ReportStore.complete_report_job(
        job.report_id,
        'worker',
        b'pdf-content',
        content_type='application/pdf',
        metadata={'renderer': 'pdf'},
        cache_key=None,
        is_personalized=True,
        now=110,
    )

    owner_status = ReportStore.get_report_job(
        job.report_id,
        account_id='owner-a',
    )
    owner_artifact = ReportStore.get_report_job(
        job.report_id,
        account_id='owner-a',
        include_artifact=True,
    )
    other_owner = ReportStore.get_report_job(
        job.report_id,
        account_id='owner-b',
        include_artifact=True,
    )
    global_status = ReportStore.get_report_job(
        job.report_id,
        account_id=None,
    )

    assert owner_status is not None
    assert owner_status.artifact is None
    assert owner_status.expires_at == 3710
    assert owner_artifact is not None
    assert owner_artifact.artifact == b'pdf-content'
    assert other_owner is None
    assert global_status is None
    assert ReportStore.cleanup_expired_report_jobs(now=3709) == 0
    assert ReportStore.cleanup_expired_report_jobs(now=3710) == 1


def test_cli_artifact_uses_the_shared_report_store(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database: SQLiteReportDatabase = SQLiteReportDatabase(
        tmp_path / 'report_store.sqlite3',
    )
    with database.connection() as connection:
        create_report_schema(connection)
    monkeypatch.setattr(ReportStore, 'report_database', database)

    report_id: str = ReportStore.create_cli_artifact(
        account_id='cli-owner',
        resource='MSFT.US',
        filename='analysis.pdf',
        report_format='pdf',
        content_type='application/pdf',
        artifact=b'pdf-content',
        request={'ticker': 'MSFT.US'},
        metadata={'generator': 'Analyze'},
        is_personalized=False,
        cache_key='canonical-key',
        now=20,
    )
    owner_report = ReportStore.get_report_job(
        report_id,
        account_id='cli-owner',
        include_artifact=True,
    )

    assert owner_report is not None
    assert owner_report.status == 'COMPLETED'
    assert owner_report.source == 'cli'
    assert owner_report.artifact == b'pdf-content'
    assert owner_report.expires_at == 3620
