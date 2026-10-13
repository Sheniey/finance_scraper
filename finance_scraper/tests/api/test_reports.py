 
import asyncio
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError
import yaml

from datatypes.ticker import Ticker
from finance.services.account.models import Account
from finance.types.report_mode import ReportMode
from finance.renderers.yaml.renderer import YAMLRenderer
from finance.services.database import close_database_pools

from api.core.database import initialize_api_database
from api.models.report import ReportFormat, ReportJob, ReportStatus
from api.repositories import report as ReportRepository
from api.schemas.report import ReportCreate
from api.services import report_worker
import api.routers.reports as reports_router


def _account_token(
    client: TestClient,
    email: str,
    password: str,
) -> str:
    response = client.post(
        '/auth/login',
        json={'email': email, 'password': password},
    )
    assert response.status_code == 200, response.text
    return response.json()['access_token']


def _user_token(client: TestClient) -> str:
    return _account_token(
        client,
        'user@example.com',
        'user-password',
    )


def _report_job(
    account_id: str,
    *,
    status: ReportStatus = ReportStatus.PENDING,
    artifact: bytes | None = None,
    completed_at: int | None = None,
) -> ReportJob:
    return ReportJob(
        report_id='rep_test123',
        account_id=account_id,
        ticker='AAPL',
        request={
            'ticker': 'AAPL',
            'filename': 'quarterly.json',
            'explain': False,
            'mode': 'custom',
            'charts': True,
            'ml_horizon': 10,
        },
        status=status,
        file_name='quarterly.json',
        report_format='json',
        content_type='application/json',
        metadata={},
        artifact=artifact,
        cache_key=None,
        is_personalized=False,
        source='api',
        error_code=None,
        created_at=1_700_000_000,
        updated_at=1_700_000_000,
        started_at=None,
        completed_at=completed_at,
        expires_at=None,
    )


def test_report_post_selects_the_artifact_downloaded_later(
    api_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, state = api_client
    account = next(
        item
        for item in state['accounts'].values()
        if str(item.email) == 'user@example.com'
    )
    token: str = _user_token(client)
    headers: dict[str, str] = {'Authorization': f'Bearer {token}'}
    pending_job: ReportJob = _report_job(str(account.id))
    jobs: dict[str, ReportJob] = {pending_job.report_id: pending_job}

    async def create_report_job(
        account_id: str,
        payload: ReportCreate,
    ) -> ReportJob:
        assert account_id == str(account.id)
        assert payload.filename == 'quarterly.json'
        assert payload.ticker == 'AAPL'
        assert payload.report_format is ReportFormat.JSON
        return pending_job

    async def get_report_job(
        report_id: str,
        account_id: str | None,
        *,
        include_artifact: bool = False,
    ) -> ReportJob | None:
        job: ReportJob | None = jobs.get(report_id)
        if (
            job is None
            or (
                account_id is not None
                and job.account_id != account_id
            )
        ):
            return None
        return job

    async def list_report_jobs(
        account_id: str | None,
    ) -> list[ReportJob]:
        return [
            job
            for job in jobs.values()
            if account_id is None or job.account_id == account_id
        ]

    monkeypatch.setattr(
        reports_router.ReportRepository,
        'create_report_job',
        create_report_job,
    )
    monkeypatch.setattr(
        reports_router.ReportRepository,
        'get_report_job',
        get_report_job,
    )
    monkeypatch.setattr(
        reports_router.ReportRepository,
        'list_report_jobs',
        list_report_jobs,
    )

    create_response = client.post(
        '/reports',
        headers=headers,
        json={
            'ticker': 'aapl',
            'filename': 'quarterly.json',
        },
    )
    assert create_response.status_code == 202, create_response.text
    assert create_response.json()['status'] == 'PENDING'
    assert create_response.json()['filename'] == 'quarterly.json'
    assert create_response.json()['report_format'] == 'json'

    completed_at: int = 1_700_000_010
    jobs[pending_job.report_id] = replace(
        pending_job,
        status=ReportStatus.COMPLETED,
        artifact=b'{"ticker":"AAPL"}',
        completed_at=completed_at,
        updated_at=completed_at,
        expires_at=completed_at + 3600,
    )

    status_response = client.get(
        f'/reports/{pending_job.report_id}',
        headers=headers,
    )
    download_response = client.get(
        f'/reports/{pending_job.report_id}/download',
        headers=headers,
    )
    list_response = client.get(
        '/reports/me',
        params={'filter': '{"report_format":"json"}'},
        headers=headers,
    )
    admin_token: str = _account_token(
        client,
        'admin@example.com',
        'admin-password',
    )
    admin_list_response = client.get(
        '/reports',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    admin_report_response = client.get(
        f'/reports/{pending_job.report_id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert status_response.status_code == 200
    assert status_response.json()['download_url'] == (
        f'/reports/{pending_job.report_id}/download'
    )
    assert download_response.status_code == 200
    assert download_response.content == b'{"ticker":"AAPL"}'
    assert 'quarterly.json' in download_response.headers['content-disposition']
    assert list_response.status_code == 200
    assert list_response.json()['pagination']['total'] == 1
    assert admin_list_response.status_code == 200
    assert admin_list_response.json()['pagination']['total'] == 1
    assert admin_report_response.status_code == 200


def test_xlsx_report_format_is_supported_by_the_api_schema() -> None:
    payload: ReportCreate = ReportCreate(
        ticker='aapl',
        filename='AAPL.xlsx',
    )

    assert payload.ticker == 'AAPL'
    assert payload.report_format is ReportFormat.XLSX
    assert (
        payload.report_format.content_type
        == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


def test_personalized_artifacts_are_downloadable_only_by_their_owner(
    api_client,
) -> None:
    client, state = api_client
    owner = next(
        item
        for item in state['accounts'].values()
        if str(item.email) == 'user@example.com'
    )
    owner_token: str = _user_token(client)
    admin_token: str = _account_token(
        client,
        'admin@example.com',
        'admin-password',
    )

    async def create_completed_job() -> str:
        job: ReportJob = await ReportRepository.create_report_job(
            str(owner.id),
            ReportCreate(
                ticker='AAPL',
                filename='private.pdf',
                mode=ReportMode.CLASSIC,
            ),
        )
        claimed_job: ReportJob | None = (
            await ReportRepository.claim_next_report_job('privacy-test')
        )
        assert claimed_job is not None
        assert claimed_job.report_id == job.report_id
        assert await ReportRepository.complete_report_job(
            job.report_id,
            'privacy-test',
            b'private-pdf',
            content_type='application/pdf',
            metadata={},
            cache_key=None,
            is_personalized=True,
        )
        return job.report_id

    report_id: str = asyncio.run(create_completed_job())
    owner_download = client.get(
        f'/reports/{report_id}/download',
        headers={'Authorization': f'Bearer {owner_token}'},
    )
    admin_download = client.get(
        f'/reports/{report_id}/download',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert owner_download.status_code == 200
    assert owner_download.content == b'private-pdf'
    assert admin_download.status_code == 404


def test_report_generation_rate_limit_is_configured_per_account(
    api_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, state = api_client
    account = next(
        item
        for item in state['accounts'].values()
        if str(item.email) == 'user@example.com'
    )
    token: str = _user_token(client)
    headers: dict[str, str] = {'Authorization': f'Bearer {token}'}
    call_count: int = 0

    async def create_report_job(
        account_id: str,
        payload: ReportCreate,
    ) -> ReportJob:
        nonlocal call_count
        call_count += 1
        return replace(
            _report_job(str(account.id)),
            report_id=f'rep_{call_count}',
            account_id=account_id,
        )

    monkeypatch.setattr(
        reports_router.ReportRepository,
        'create_report_job',
        create_report_job,
    )

    responses = [
        client.post(
            '/reports',
            headers=headers,
            json={'ticker': 'AAPL', 'filename': 'AAPL.pdf'},
        )
        for _ in range(4)
    ]

    assert [response.status_code for response in responses] == [
        202,
        202,
        202,
        429,
    ]
    assert responses[-1].json()['error'] == 'RATE_LIMIT_EXCEEDED'


def test_report_create_validates_safe_filename_and_format() -> None:
    default_report: ReportCreate = ReportCreate(
        ticker='aapl',
        filename='AAPL.pdf',
    )
    yaml_report: ReportCreate = ReportCreate(
        ticker='msft',
        filename='year-end.yaml',
    )

    assert default_report.ticker == 'AAPL'
    assert default_report.explain is False
    assert default_report.mode is ReportMode.CUSTOM
    assert default_report.charts is True
    assert default_report.ml_horizon == 15
    assert default_report.filename == 'AAPL.pdf'
    assert default_report.report_format is ReportFormat.PDF
    assert yaml_report.report_format is ReportFormat.YAML
    with pytest.raises(ValidationError):
        ReportCreate(ticker='AAPL', filename='../../outside.pdf')
    with pytest.raises(ValidationError):
        ReportCreate(ticker='AAPL', filename='report.csv')
    with pytest.raises(ValidationError):
        ReportCreate(ticker='AAPL', filename='CON.pdf')
    with pytest.raises(ValidationError):
        ReportCreate(ticker='AAPL', filename='report')
    with pytest.raises(ValidationError):
        ReportCreate(ticker='AAPL')
    assert ReportCreate(
        ticker='aapl.n',
        filename='quarterly.PDF',
    ).report_format is ReportFormat.PDF


def test_report_strategy_selects_renderer_from_filename_extension() -> None:
    from finance.renderers import smart_render_strategy

    expected_renderers: dict[str, str] = {
        'report.pdf': 'PDFRenderer',
        'report.json': 'JSONRenderer',
        'report.yaml': 'YAMLRenderer',
        'report.txt': 'TXTRenderer',
    }

    for filename, renderer_name in expected_renderers.items():
        renderer = smart_render_strategy.match(filename)
        assert renderer.__class__.__name__ == renderer_name


def test_yaml_renderer_serializes_json_compatible_report_values(
    tmp_path: Path,
) -> None:
    class SerializableTicker(BaseModel):
        symbol: str

    class SerializableAccount(BaseModel):
        name: str
        email: str

    class SerializableReport(BaseModel):
        account_id: UUID
        ticker: SerializableTicker
        account: SerializableAccount

    output: Path = tmp_path / 'report.yaml'
    YAMLRenderer().render(
        SerializableReport(
            account_id=UUID('a3dcb651-4864-4bc2-a45d-3d2b51d628f8'),
            ticker=SerializableTicker(symbol='AAPL'),
            account=SerializableAccount(
                name='Report Owner',
                email='report-owner@example.com',
            ),
        ),
        str(output),
    )
    payload: dict[str, str] = yaml.safe_load(
        output.read_text(encoding='utf-8'),
    )

    assert payload['account_id'] == 'a3dcb651-4864-4bc2-a45d-3d2b51d628f8'
    assert payload['ticker'] == {'symbol': 'AAPL'}
    assert payload['account']['name'] == 'Report Owner'


def test_report_worker_persists_completion_failure_and_expiry(
    api_test_paths: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account_id: str = str(uuid4())
    account: Account = Account(
        id=uuid4(),
        account_id=uuid4(),
        name='Report Owner',
        email='report-owner@example.com',
    )

    class FakeRenderer:
        def render(self, report: object, output: str) -> None:
            Path(output).write_text('generated artifact', encoding='utf-8')

    async def get_account(requested_id: str) -> Account | None:
        return account if requested_id == account_id else None

    async def generate_report(
        requested_account: Account,
        ticker: Ticker,
        **kwargs: Any,
    ) -> object:
        return object()

    monkeypatch.setattr(report_worker, 'get_by_id', get_account)
    monkeypatch.setattr(report_worker, 'generate_report', generate_report)
    monkeypatch.setattr(
        report_worker,
        'get_report_cache_key',
        lambda *args, **kwargs: 'cache-key',
    )
    strategy_calls: list[str] = []

    class FakeStrategy:
        def match(self, filename: str) -> FakeRenderer:
            strategy_calls.append(filename)
            return FakeRenderer()

    monkeypatch.setattr(report_worker, 'smart_render_strategy', FakeStrategy())

    async def scenario() -> None:
        try:
            await initialize_api_database()
            worker_id: str = 'worker-test'
            created_job: ReportJob = await ReportRepository.create_report_job(
                account_id,
                ReportCreate(
                    ticker='AAPL',
                    filename='complete.TXT',
                ),
            )
            claimed_job: ReportJob | None = (
                await ReportRepository.claim_next_report_job(worker_id)
            )
            assert claimed_job is not None
            assert claimed_job.report_id == created_job.report_id
            await report_worker._process_report_job(claimed_job, worker_id)

            completed_job: ReportJob | None = (
                await ReportRepository.get_report_job(
                    created_job.report_id,
                    account_id,
                    include_artifact=True,
                )
            )
            assert completed_job is not None
            assert completed_job.status is ReportStatus.COMPLETED
            assert completed_job.artifact == b'generated artifact'
            assert strategy_calls == ['complete.txt']
            assert (
                completed_job.expires_at
                == completed_job.completed_at + 15 * 24 * 60 * 60
            )
            await ReportRepository.apply_report_retention(600)
            completed_job = await ReportRepository.get_report_job(
                created_job.report_id,
                account_id,
                include_artifact=True,
            )
            assert completed_job is not None
            assert completed_job.expires_at == completed_job.completed_at + 600

            assert completed_job.expires_at is not None
            deleted: int = await ReportRepository.cleanup_expired_report_jobs(
                now=completed_job.expires_at,
            )
            assert deleted == 1
            assert await ReportRepository.get_report_job(
                created_job.report_id,
                account_id,
            ) is None

            failed_request: ReportJob = await ReportRepository.create_report_job(
                account_id,
                ReportCreate(
                    ticker='MSFT',
                    filename='failed.txt',
                ),
            )
            failed_claim: ReportJob | None = (
                await ReportRepository.claim_next_report_job(worker_id)
            )
            assert failed_claim is not None

            async def fail_report(
                requested_account: Account,
                ticker: Ticker,
                **kwargs: Any,
            ) -> object:
                raise ValueError('invalid report settings')

            monkeypatch.setattr(report_worker, 'generate_report', fail_report)
            await report_worker._process_report_job(failed_claim, worker_id)
            failed_job: ReportJob | None = (
                await ReportRepository.get_report_job(
                    failed_request.report_id,
                    account_id,
                )
            )
            assert failed_job is not None
            assert failed_job.status is ReportStatus.FAILED
            assert failed_job.error_code == 'REPORT_REQUEST_INVALID'
        finally:
            await close_database_pools()

    asyncio.run(scenario())


def test_expired_report_lease_can_be_reclaimed_after_restart(
    api_test_paths: Path,
) -> None:
    account_id: str = str(uuid4())

    async def scenario() -> None:
        try:
            await initialize_api_database()
            job: ReportJob = await ReportRepository.create_report_job(
                account_id,
                ReportCreate(ticker='AAPL', filename='AAPL.pdf'),
            )
            first_claim: ReportJob | None = (
                await ReportRepository.claim_next_report_job(
                    'stopped-worker',
                    now=10_000,
                    lease_seconds=5,
                )
            )
            recovered_claim: ReportJob | None = (
                await ReportRepository.claim_next_report_job(
                    'restarted-worker',
                    now=10_006,
                    lease_seconds=30,
                )
            )

            assert first_claim is not None
            assert recovered_claim is not None
            assert recovered_claim.report_id == job.report_id
            assert recovered_claim.worker_id == 'restarted-worker'
            assert recovered_claim.status is ReportStatus.IN_PROGRESS
        finally:
            await close_database_pools()

    asyncio.run(scenario())
