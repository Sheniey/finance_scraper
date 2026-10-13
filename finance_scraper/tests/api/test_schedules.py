import asyncio
import time as time_module
from datetime import time
from pathlib import Path
from uuid import uuid4

import pytest

from finance.services.account.models import Account
from finance.services.database import close_database_pools
from finance.types.language import Language

from api.core.database import initialize_api_database
from api.models.google import GoogleAccountConnection
from api.models.report import ReportJob, ReportStatus
from api.models.schedule import ReportSchedule
from api.repositories import schedules as ScheduleRepository
from api.schemas.report import ReportCreate
from api.schemas.schedule import ScheduleCreate
import api.services.schedules as schedule_service


def test_schedule_records_and_delivery_claim_are_idempotent(
    api_test_paths: Path,
) -> None:
    async def scenario() -> None:
        try:
            await initialize_api_database()
            schedule: ScheduleCreate = ScheduleCreate(
                tickers=['aapl', 'NVDA'],
                report_format='xlsx',
                run_at=time(8, 30),
                timezone='America/Denver',
            )
            created = await ScheduleRepository.create_schedule(
                'account-test',
                schedule,
            )
            assert created.run_at == '08:30'
            assert created.tickers == ('AAPL', 'NVDA')

            status, report_ids, should_process = (
                await ScheduleRepository.claim_schedule_run(
                    created,
                    '2026-10-12',
                )
            )
            assert status == 'IN_PROGRESS'
            assert report_ids == []
            assert should_process is True
            await ScheduleRepository.update_schedule_run_reports(
                created.schedule_id,
                created.account_id,
                '2026-10-12',
                ['rep_one', 'rep_two'],
            )
            assert await ScheduleRepository.claim_schedule_delivery(
                created.schedule_id,
                created.account_id,
                '2026-10-12',
            ) is True
            assert await ScheduleRepository.claim_schedule_delivery(
                created.schedule_id,
                created.account_id,
                '2026-10-12',
            ) is False
            await ScheduleRepository.finish_schedule_run(
                created.schedule_id,
                created.account_id,
                '2026-10-12',
                'SENT',
            )
            final_status, report_ids, should_process = (
                await ScheduleRepository.claim_schedule_run(
                    created,
                    '2026-10-12',
                )
            )
            assert final_status == 'SENT'
            assert report_ids == ['rep_one', 'rep_two']
            assert should_process is False

            other_account_schedules = (
                await ScheduleRepository.list_schedules('other-account')
            )
            assert other_account_schedules == []
        finally:
            await close_database_pools()

    asyncio.run(scenario())


def test_due_schedule_sends_completed_reports_for_its_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_id: str = str(uuid4())
    schedule_id: str = 'sch_' + 'a' * 32
    schedule: ReportSchedule = ReportSchedule(
        schedule_id=schedule_id,
        account_id=owner_id,
        tickers=('AAPL',),
        report_format='pdf',
        run_at='00:00',
        timezone='UTC',
        explain=False,
        mode='custom',
        charts=True,
        ml_horizon=15,
        enabled=True,
        last_run_date=None,
        last_run_status=None,
        last_error=None,
        created_at=int(time_module.time()),
        updated_at=int(time_module.time()),
    )
    account: Account = Account(
        name='Owner',
        email='owner@example.com',
        language=Language(code='en', name='English'),
    )
    connection: GoogleAccountConnection = GoogleAccountConnection(
        account_id=owner_id,
        google_email='gmail-owner@example.com',
        scopes=(
            'openid',
            'email',
            'https://www.googleapis.com/auth/gmail.send',
        ),
        connected_at=1,
        updated_at=1,
    )
    scheduled_date: str = schedule_service._scheduled_date(schedule) or ''
    report_id: str = schedule_service._scheduled_report_id(
        schedule_id,
        scheduled_date,
        'AAPL',
    )
    now: int = int(time_module.time())
    completed_report: ReportJob = ReportJob(
        report_id=report_id,
        account_id=owner_id,
        ticker='AAPL',
        request={},
        status=ReportStatus.COMPLETED,
        file_name='AAPL-report.pdf',
        report_format='pdf',
        content_type='application/pdf',
        metadata={},
        artifact=b'%PDF report',
        cache_key=None,
        is_personalized=False,
        source='api',
        error_code=None,
        created_at=now,
        updated_at=now,
        started_at=now,
        completed_at=now,
        expires_at=now + 3600,
    )
    sent_messages: list[tuple[str, str, str, list[object]]] = []
    finished_statuses: list[str] = []

    async def get_schedule(requested_schedule_id: str):
        assert requested_schedule_id == schedule_id
        return schedule

    async def get_account(account_id: str):
        assert account_id == owner_id
        return account

    async def get_google_connection(account_id: str):
        assert account_id == owner_id
        return connection

    async def claim_run(requested_schedule, run_date: str):
        assert requested_schedule.account_id == owner_id
        assert run_date == scheduled_date
        return 'IN_PROGRESS', [], True

    async def update_report_ids(*args):
        return None

    async def create_report_job(
        account_id: str,
        payload: ReportCreate,
        *,
        report_id: str,
    ):
        assert account_id == owner_id
        assert payload.ticker == 'AAPL'
        assert report_id == completed_report.report_id
        return completed_report

    async def wait_for_reports(account_id: str, report_ids: list[str]):
        assert account_id == owner_id
        assert report_ids == [completed_report.report_id]
        return [completed_report]

    async def claim_delivery(*args):
        return True

    async def send_email(account_id: str, subject: str, body: str, attachments):
        sent_messages.append((account_id, subject, body, list(attachments)))

    async def finish_run(
        schedule_id: str,
        account_id: str,
        run_date: str,
        run_status: str,
        *,
        error_code: str | None = None,
    ):
        finished_statuses.append(run_status)

    monkeypatch.setattr(
        schedule_service.ScheduleRepository,
        'get_schedule_by_id',
        get_schedule,
    )
    monkeypatch.setattr(schedule_service, 'get_by_id', get_account)
    monkeypatch.setattr(
        schedule_service.GoogleRepository,
        'get_google_connection',
        get_google_connection,
    )
    monkeypatch.setattr(
        schedule_service.ScheduleRepository,
        'claim_schedule_run',
        claim_run,
    )
    monkeypatch.setattr(
        schedule_service.ScheduleRepository,
        'update_schedule_run_reports',
        update_report_ids,
    )
    monkeypatch.setattr(
        schedule_service.ReportRepository,
        'create_report_job',
        create_report_job,
    )
    monkeypatch.setattr(schedule_service, '_wait_for_reports', wait_for_reports)
    monkeypatch.setattr(
        schedule_service.ScheduleRepository,
        'claim_schedule_delivery',
        claim_delivery,
    )
    monkeypatch.setattr(schedule_service, 'send_google_email', send_email)
    monkeypatch.setattr(
        schedule_service.ScheduleRepository,
        'finish_schedule_run',
        finish_run,
    )

    result = asyncio.run(schedule_service.run_scheduled_report(schedule_id))

    assert result.status == 'SENT'
    assert result.report_ids == (report_id,)
    assert len(sent_messages) == 1
    assert sent_messages[0][0] == owner_id
    assert 'AAPL' in sent_messages[0][1]
    assert 'Hello Owner' in sent_messages[0][2]
    assert sent_messages[0][3][0].content == b'%PDF report'
    assert finished_statuses == ['SENT']
