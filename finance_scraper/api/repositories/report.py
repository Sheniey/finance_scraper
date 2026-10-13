import asyncio
import sqlite3
import time
from collections.abc import Mapping
from typing import Any

from finance.services.report_store import reports as ReportStore
from finance.services.report_store.models import StoredReportJob

from api.core.config import IS_DEV, settings
from api.core.database import api_transaction
from api.models.report import ReportJob, ReportStatus
from api.schemas.report import ReportCreate


def _to_report_job(job: StoredReportJob) -> ReportJob:
    return ReportJob(
        report_id=job.report_id,
        account_id=job.account_id,
        ticker=job.resource,
        request=job.request,
        status=ReportStatus(job.status),
        file_name=job.filename,
        report_format=job.report_format,
        content_type=job.content_type,
        metadata=job.metadata,
        artifact=job.artifact,
        cache_key=job.cache_key,
        is_personalized=job.is_personalized,
        source=job.source,
        error_code=job.error_code,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        expires_at=job.expires_at,
        worker_id=job.worker_id,
        lease_until=job.lease_until,
    )


def _is_expired(job: StoredReportJob, *, now: int | None = None) -> bool:
    if IS_DEV or job.expires_at is None:
        return False
    checked_at: int = now if now is not None else int(time.time())
    return job.expires_at <= checked_at


async def create_report_job(
    account_id: str,
    payload: ReportCreate,
    *,
    report_id: str | None = None,
) -> ReportJob:
    if report_id is not None:
        existing_job: ReportJob | None = await get_report_job(
            report_id,
            account_id,
        )
        if existing_job is not None:
            return existing_job

    try:
        job: StoredReportJob = await asyncio.to_thread(
            ReportStore.create_report_job,
            account_id=account_id,
            resource=payload.ticker,
            request=payload.model_dump(mode='json'),
            filename=payload.filename,
            report_format=payload.report_format.value,
            content_type=payload.report_format.content_type,
            metadata={'source': 'api'},
            report_id=report_id,
        )
    except sqlite3.IntegrityError:
        if report_id is None:
            raise
        existing_job = await get_report_job(report_id, account_id)
        if existing_job is None:
            raise
        return existing_job
    return _to_report_job(job)


async def get_report_job(
    report_id: str,
    account_id: str | None,
    *,
    include_artifact: bool = False,
) -> ReportJob | None:
    job: StoredReportJob | None = await asyncio.to_thread(
        ReportStore.get_report_job,
        report_id,
        account_id=account_id,
        include_artifact=include_artifact,
    )
    if job is not None and _is_expired(job):
        return None
    return _to_report_job(job) if job is not None else None


async def list_report_jobs(account_id: str | None) -> list[ReportJob]:
    jobs: list[StoredReportJob] = await asyncio.to_thread(
        ReportStore.list_report_jobs,
        account_id=account_id,
    )
    return [
        _to_report_job(job)
        for job in jobs
        if not _is_expired(job)
    ]


async def claim_next_report_job(
    worker_id: str,
    *,
    now: int | None = None,
    lease_seconds: int = 120,
) -> ReportJob | None:
    job: StoredReportJob | None = await asyncio.to_thread(
        ReportStore.claim_next_report_job,
        worker_id,
        now=now,
        lease_seconds=lease_seconds,
    )
    return _to_report_job(job) if job is not None else None


async def renew_report_lease(
    report_id: str,
    worker_id: str,
    *,
    now: int | None = None,
    lease_seconds: int = 120,
) -> bool:
    return await asyncio.to_thread(
        ReportStore.renew_report_lease,
        report_id,
        worker_id,
        now=now,
        lease_seconds=lease_seconds,
    )


async def complete_report_job(
    report_id: str,
    worker_id: str,
    artifact: bytes,
    *,
    content_type: str,
    metadata: Mapping[str, Any],
    cache_key: str | None,
    is_personalized: bool,
    now: int | None = None,
) -> bool:
    return await asyncio.to_thread(
        ReportStore.complete_report_job,
        report_id,
        worker_id,
        artifact,
        content_type=content_type,
        metadata=metadata,
        cache_key=cache_key,
        is_personalized=is_personalized,
        now=now,
        ttl_seconds=settings.api.report_retention_seconds,
    )


async def fail_report_job(
    report_id: str,
    worker_id: str,
    error_code: str,
    *,
    is_personalized: bool = False,
    now: int | None = None,
) -> bool:
    return await asyncio.to_thread(
        ReportStore.fail_report_job,
        report_id,
        worker_id,
        error_code,
        is_personalized=is_personalized,
        now=now,
        ttl_seconds=settings.api.report_retention_seconds,
    )


async def delete_report_job(
    report_id: str,
    account_id: str | None,
) -> bool:
    return await asyncio.to_thread(
        ReportStore.delete_report_job,
        report_id,
        account_id=account_id,
    )


async def delete_account_report_jobs(account_id: str) -> int:
    return await asyncio.to_thread(
        ReportStore.delete_report_jobs,
        account_id=account_id,
    )


async def delete_all_report_jobs(account_id: str | None) -> int:
    return await asyncio.to_thread(
        ReportStore.delete_report_jobs,
        account_id=account_id,
    )


async def cleanup_expired_report_jobs(
    *,
    now: int | None = None,
) -> int:
    return await asyncio.to_thread(
        ReportStore.cleanup_expired_report_jobs,
        now=now,
    )


async def apply_report_retention(ttl_seconds: int) -> int:
    return await asyncio.to_thread(
        ReportStore.update_report_retention,
        ttl_seconds,
    )


async def cleanup_expired_tokens(*, now: int | None = None) -> int:
    cleanup_at: int = now if now is not None else int(time.time())
    async with api_transaction() as connection:
        result = await connection.execute(
            '''
            DELETE FROM api_tokens
            WHERE expires_at <= ?
            ''',
            (cleanup_at,),
        )
    return result.rowcount
