import asyncio
import hashlib
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from datatypes.ticker import Ticker
from finance.services.account import get_by_id
from finance.types.report_mode import ReportMode

from api.exceptions.google import (
    GoogleAccountNotConnectedError,
    GoogleOAuthNotConfiguredError,
    GoogleOAuthProviderError,
)
from api.models.report import ReportJob, ReportStatus
from api.models.schedule import ReportSchedule, ScheduleRunResult
from api.repositories import google as GoogleRepository
from api.repositories import report as ReportRepository
from api.repositories import schedules as ScheduleRepository
from api.schemas.report import ReportCreate
from api.services.google_mail import (
    GoogleEmailAttachment,
    send_google_email,
)


_REPORT_POLL_SECONDS: float = 1.0
_REPORT_TIMEOUT_SECONDS: int = 2 * 60 * 60


def _scheduled_report_id(
    schedule_id: str,
    scheduled_date: str,
    ticker: str,
) -> str:
    key: bytes = f'{schedule_id}:{scheduled_date}:{ticker}'.encode('utf-8')
    digest: str = hashlib.sha256(key).hexdigest()[:32]
    return f'rep_{digest}'


def _scheduled_filename(
    ticker: str,
    scheduled_date: str,
    report_format: str,
) -> str:
    normalized_ticker: str = ticker.replace('.', '-')
    return f'{normalized_ticker}-{scheduled_date}.{report_format}'


def _scheduled_date(schedule: ReportSchedule) -> str | None:
    now: datetime = datetime.now(ZoneInfo(schedule.timezone))
    if now.strftime('%H:%M') < schedule.run_at:
        return None
    return now.date().isoformat()


def _report_email_content(
    account_name: str,
    tickers: tuple[str, ...],
    scheduled_date: str,
    language_code: str,
) -> tuple[str, str]:
    ticker_label: str = ', '.join(tickers)
    if language_code.casefold().startswith('en'):
        subject: str = (
            f'Finance Scraper report — {ticker_label} — {scheduled_date}'
        )
        body: str = (
            f'Hello {account_name},\n\n'
            f'Your scheduled Finance Scraper report for {ticker_label} '
            f'on {scheduled_date} is attached.\n\n'
            'The message was sent from your connected Google account.'
        )
        return subject, body
    subject = (
        f'Finance Scraper — Reporte de {ticker_label} — {scheduled_date}'
    )
    body = (
        f'Hola {account_name},\n\n'
        f'Adjuntamos tu reporte programado de Finance Scraper para '
        f'{ticker_label} del {scheduled_date}.\n\n'
        'El correo se envió desde tu cuenta de Google autorizada.'
    )
    return subject, body


async def _wait_for_reports(
    account_id: str,
    report_ids: list[str],
) -> list[ReportJob] | None:
    deadline: float = time.monotonic() + _REPORT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        jobs: list[ReportJob | None] = await asyncio.gather(
            *(
                ReportRepository.get_report_job(report_id, account_id)
                for report_id in report_ids
            ),
        )
        if any(job is None for job in jobs):
            return None
        typed_jobs: list[ReportJob] = [
            job
            for job in jobs
            if job is not None
        ]
        if any(job.status is ReportStatus.FAILED for job in typed_jobs):
            return typed_jobs
        if all(job.status is ReportStatus.COMPLETED for job in typed_jobs):
            artifact_jobs: list[ReportJob | None] = await asyncio.gather(
                *(
                    ReportRepository.get_report_job(
                        report_id,
                        account_id,
                        include_artifact=True,
                    )
                    for report_id in report_ids
                ),
            )
            return [
                job
                for job in artifact_jobs
                if job is not None
            ]
        await asyncio.sleep(_REPORT_POLL_SECONDS)
    return None


async def run_scheduled_report(
    schedule_id: str,
) -> ScheduleRunResult:
    schedule: ReportSchedule | None = (
        await ScheduleRepository.get_schedule_by_id(schedule_id)
    )
    if schedule is None:
        return ScheduleRunResult(
            schedule_id=schedule_id,
            scheduled_date='',
            status='NOT_FOUND',
            report_ids=(),
        )
    if not schedule.enabled:
        return ScheduleRunResult(
            schedule_id=schedule_id,
            scheduled_date='',
            status='DISABLED',
            report_ids=(),
        )

    scheduled_date: str | None = _scheduled_date(schedule)
    if scheduled_date is None:
        return ScheduleRunResult(
            schedule_id=schedule_id,
            scheduled_date='',
            status='NOT_DUE',
            report_ids=(),
        )

    run_status, report_ids, should_process = (
        await ScheduleRepository.claim_schedule_run(
            schedule,
            scheduled_date,
        )
    )
    if not should_process:
        return ScheduleRunResult(
            schedule_id=schedule_id,
            scheduled_date=scheduled_date,
            status=run_status,
            report_ids=tuple(report_ids),
        )

    account = await get_by_id(schedule.account_id)
    if account is None:
        await ScheduleRepository.finish_schedule_run(
            schedule.schedule_id,
            schedule.account_id,
            scheduled_date,
            'FAILED',
            error_code='ACCOUNT_NOT_FOUND',
        )
        return ScheduleRunResult(
            schedule_id=schedule_id,
            scheduled_date=scheduled_date,
            status='FAILED',
            report_ids=tuple(report_ids),
        )

    connection = await GoogleRepository.get_google_connection(
        schedule.account_id,
    )
    if connection is None:
        await ScheduleRepository.finish_schedule_run(
            schedule.schedule_id,
            schedule.account_id,
            scheduled_date,
            'FAILED',
            error_code='GOOGLE_ACCOUNT_NOT_CONNECTED',
        )
        return ScheduleRunResult(
            schedule_id=schedule_id,
            scheduled_date=scheduled_date,
            status='FAILED',
            report_ids=tuple(report_ids),
        )

    report_ids = [
        _scheduled_report_id(schedule.schedule_id, scheduled_date, ticker)
        for ticker in schedule.tickers
    ]
    await ScheduleRepository.update_schedule_run_reports(
        schedule.schedule_id,
        schedule.account_id,
        scheduled_date,
        report_ids,
    )
    for ticker, report_id in zip(schedule.tickers, report_ids, strict=True):
        payload: ReportCreate = ReportCreate(
            ticker=ticker,
            filename=_scheduled_filename(
                ticker,
                scheduled_date,
                schedule.report_format,
            ),
            explain=schedule.explain,
            mode=ReportMode(schedule.mode),
            charts=schedule.charts,
            ml_horizon=schedule.ml_horizon,
        )
        await ReportRepository.create_report_job(
            schedule.account_id,
            payload,
            report_id=report_id,
        )

    completed_jobs: list[ReportJob] | None = await _wait_for_reports(
        schedule.account_id,
        report_ids,
    )
    if (
        completed_jobs is None
        or len(completed_jobs) != len(report_ids)
        or any(
        job.status is not ReportStatus.COMPLETED
        or job.artifact is None
        for job in completed_jobs
        )
    ):
        failed_job: ReportJob | None = next(
            (
                job
                for job in completed_jobs or []
                if job.status is ReportStatus.FAILED
            ),
            None,
        )
        error_code: str = (
            failed_job.error_code
            if failed_job is not None and failed_job.error_code
            else 'REPORT_GENERATION_FAILED'
        )
        await ScheduleRepository.finish_schedule_run(
            schedule.schedule_id,
            schedule.account_id,
            scheduled_date,
            'FAILED',
            error_code=error_code,
        )
        return ScheduleRunResult(
            schedule_id=schedule_id,
            scheduled_date=scheduled_date,
            status='FAILED',
            report_ids=tuple(report_ids),
        )

    did_claim_delivery: bool = (
        await ScheduleRepository.claim_schedule_delivery(
            schedule.schedule_id,
            schedule.account_id,
            scheduled_date,
        )
    )
    if not did_claim_delivery:
        return ScheduleRunResult(
            schedule_id=schedule_id,
            scheduled_date=scheduled_date,
            status='SENDING',
            report_ids=tuple(report_ids),
        )

    attachments: list[GoogleEmailAttachment] = [
        GoogleEmailAttachment(
            filename=job.file_name,
            content_type=job.content_type,
            content=job.artifact or b'',
        )
        for job in completed_jobs
    ]
    subject, text_body = _report_email_content(
        account.name,
        schedule.tickers,
        scheduled_date,
        account.language.code,
    )
    try:
        await send_google_email(
            schedule.account_id,
            subject,
            text_body,
            attachments,
        )
    except GoogleAccountNotConnectedError:
        await ScheduleRepository.finish_schedule_run(
            schedule.schedule_id,
            schedule.account_id,
            scheduled_date,
            'FAILED',
            error_code='GOOGLE_ACCOUNT_NOT_CONNECTED',
        )
        return ScheduleRunResult(
            schedule_id=schedule_id,
            scheduled_date=scheduled_date,
            status='FAILED',
            report_ids=tuple(report_ids),
        )
    except GoogleOAuthNotConfiguredError:
        await ScheduleRepository.finish_schedule_run(
            schedule.schedule_id,
            schedule.account_id,
            scheduled_date,
            'FAILED',
            error_code='GOOGLE_OAUTH_NOT_CONFIGURED',
        )
        return ScheduleRunResult(
            schedule_id=schedule_id,
            scheduled_date=scheduled_date,
            status='FAILED',
            report_ids=tuple(report_ids),
        )
    except GoogleOAuthProviderError:
        await ScheduleRepository.finish_schedule_run(
            schedule.schedule_id,
            schedule.account_id,
            scheduled_date,
            'DELIVERY_UNKNOWN',
            error_code='EMAIL_DELIVERY_UNKNOWN',
        )
        return ScheduleRunResult(
            schedule_id=schedule_id,
            scheduled_date=scheduled_date,
            status='DELIVERY_UNKNOWN',
            report_ids=tuple(report_ids),
        )

    await ScheduleRepository.finish_schedule_run(
        schedule.schedule_id,
        schedule.account_id,
        scheduled_date,
        'SENT',
    )
    return ScheduleRunResult(
        schedule_id=schedule_id,
        scheduled_date=scheduled_date,
        status='SENT',
        report_ids=tuple(report_ids),
    )


async def run_due_scheduled_reports() -> list[ScheduleRunResult]:
    schedules: list[ReportSchedule] = (
        await ScheduleRepository.list_enabled_schedules()
    )
    results: list[ScheduleRunResult] = []
    for schedule in schedules:
        result: ScheduleRunResult = await run_scheduled_report(
            schedule.schedule_id,
        )
        if result.status not in {'NOT_DUE', 'SENT', 'SENDING'}:
            results.append(result)
    return results
