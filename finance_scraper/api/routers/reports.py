
from datetime import UTC, datetime
from urllib.parse import quote
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import PlainTextResponse

from finance.services.account import Account
from finance.services.account.models import WatchlistItem

from api.core.config import settings
from api.core.roles import Roles
from api.exceptions.report import (
    ReportArtifactNotFoundError,
    ReportNotFoundError,
    ReportNotReadyError,
)
from api.models.report import ReportJob, ReportStatus
from api.repositories import report as ReportRepository
from api.schemas.base import CollectionResponse
from api.schemas.query import CollectionQuery, get_collection_query
from api.schemas.report import (
    ReportBatchResponse,
    ReportCollectionResponse,
    ReportCreate,
    ReportDeleteResponse,
    ReportStatusResponse,
)
from api.services.collections import collection_response
from api.services.rate_limit import limiter
from api.services.security import require_permission


router: APIRouter = APIRouter(prefix='/reports', tags=['reports'])
_REPORT_FIELDS: set[str] = {
    'report_id',
    'status',
    'ticker',
    'filename',
    'report_format',
    'created_at',
    'updated_at',
    'started_at',
    'completed_at',
    'expires_at',
    'error_code',
    'download_url',
}
def _account_id(account: Account) -> str:
    return str(account.account_id or account.id)


def _report_scope(
    account: Account,
    *,
    include_all_for_admin: bool = True,
) -> str | None:
    role = Roles.get_role(account.role)
    if (
        include_all_for_admin
        and role is not None
        and role.has_permission('everything')
    ):
        return None
    return _account_id(account)


def _as_datetime(timestamp: int | None) -> datetime | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=UTC)


def _report_response(job: ReportJob) -> ReportStatusResponse:
    download_url: str | None = None
    if job.status is ReportStatus.COMPLETED:
        download_url = f'/reports/{job.report_id}/download'
    return ReportStatusResponse(
        report_id=job.report_id,
        status=job.status,
        ticker=job.ticker,
        filename=job.file_name,
        report_format=job.report_format,
        created_at=datetime.fromtimestamp(job.created_at, tz=UTC),
        updated_at=datetime.fromtimestamp(job.updated_at, tz=UTC),
        started_at=_as_datetime(job.started_at),
        completed_at=_as_datetime(job.completed_at),
        expires_at=_as_datetime(job.expires_at),
        error_code=job.error_code,
        download_url=download_url,
    )


async def _list_reports(
    account: Account,
    query: CollectionQuery,
    *,
    include_all_for_admin: bool = False,
) -> CollectionResponse:
    jobs: list[ReportJob] = await ReportRepository.list_report_jobs(
        _report_scope(
            account,
            include_all_for_admin=include_all_for_admin,
        ),
    )
    items: list[ReportStatusResponse] = [
        _report_response(job)
        for job in jobs
    ]
    return collection_response(
        items,
        query,
        allowed_fields=_REPORT_FIELDS,
        allowed_sort_fields={
            'report_id',
            'status',
            'ticker',
            'report_format',
            'created_at',
            'updated_at',
        },
        allowed_filter_fields={'status', 'ticker', 'report_format'},
        default_sort=('-created_at',),
    )


async def _enqueue_report(
    account: Account,
    payload: ReportCreate,
) -> ReportStatusResponse:
    job: ReportJob = await ReportRepository.create_report_job(
        _account_id(account),
        payload,
    )
    return _report_response(job)


async def _enqueue_watchlist_reports(account: Account) -> ReportBatchResponse:
    report_ids: list[str] = []
    for item in account.watchlist:
        if not isinstance(item, WatchlistItem) or not item.enabled:
            continue
        payload: ReportCreate = ReportCreate(
            ticker=item.symbol,
            filename=f'{item.symbol}.pdf',
            explain=item.llm_explanation,
            mode=item.mode,
            charts=item.charts,
            ml_horizon=item.horizon,
        )
        job: ReportJob = await ReportRepository.create_report_job(
            _account_id(account),
            payload,
        )
        report_ids.append(job.report_id)
    return ReportBatchResponse(
        report_ids=report_ids,
        count=len(report_ids),
    )


@router.get(
    '',
    response_model=ReportCollectionResponse,
    status_code=status.HTTP_200_OK,
    summary='List report statuses available to the authenticated role',
)
async def get_reports(
    query: CollectionQuery = Depends(get_collection_query),
    account: Account = Depends(require_permission('report:limited-read')),
) -> ReportCollectionResponse:
    return await _list_reports(
        account,
        query,
        include_all_for_admin=True,
    )


@router.post(
    '',
    response_model=ReportStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary='Queue a financial report',
)
@limiter.limit(
    f'{settings.security.rate_limits.report_generation_per_minute}/minute',
)
async def create_report(
    request: Request,
    response: Response,
    payload: ReportCreate,
    account: Account = Depends(require_permission('report:create')),
) -> ReportStatusResponse:
    return await _enqueue_report(account, payload)


@router.delete(
    '',
    response_model=ReportDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary='Delete all accessible report statuses and artifacts',
)
async def delete_reports(
    account: Account = Depends(require_permission('report-me:delete')),
) -> ReportDeleteResponse:
    deleted: int = await ReportRepository.delete_all_report_jobs(
        _report_scope(account),
    )
    return ReportDeleteResponse(deleted=deleted)


@router.get(
    '/me',
    response_model=ReportCollectionResponse,
    status_code=status.HTTP_200_OK,
    summary='List the authenticated account report statuses',
)
async def get_my_reports(
    query: CollectionQuery = Depends(get_collection_query),
    account: Account = Depends(require_permission('report-me:read')),
) -> ReportCollectionResponse:
    return await _list_reports(
        account,
        query,
        include_all_for_admin=False,
    )


@router.post(
    '/me',
    response_model=ReportStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary='Queue a financial report for the authenticated account',
)
@limiter.limit(
    f'{settings.security.rate_limits.report_generation_per_minute}/minute',
)
async def create_my_report(
    request: Request,
    response: Response,
    payload: ReportCreate,
    account: Account = Depends(require_permission('report:create')),
) -> ReportStatusResponse:
    return await _enqueue_report(account, payload)


@router.post(
    '/run-watchlist',
    response_model=ReportBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary='Queue financial reports for the authenticated account watchlist',
)
@limiter.limit(
    f'{settings.security.rate_limits.report_generation_per_minute}/minute',
)
async def run_watchlist_reports(
    request: Request,
    response: Response,
    account: Account = Depends(require_permission('report:create')),
) -> ReportBatchResponse:
    return await _enqueue_watchlist_reports(account)


@router.post(
    '/me/run-watchlist',
    response_model=ReportBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary='Queue financial reports for the authenticated account watchlist',
)
@limiter.limit(
    f'{settings.security.rate_limits.report_generation_per_minute}/minute',
)
async def run_my_watchlist_reports(
    request: Request,
    response: Response,
    account: Account = Depends(require_permission('report:create')),
) -> ReportBatchResponse:
    return await _enqueue_watchlist_reports(account)


@router.get(
    '/{report_id}',
    response_model=ReportStatusResponse,
    status_code=status.HTTP_200_OK,
    summary='Get a report status',
)
async def get_report(
    report_id: str,
    account: Account = Depends(require_permission('report:limited-read')),
) -> ReportStatusResponse:
    job: ReportJob | None = await ReportRepository.get_report_job(
        report_id,
        _account_id(account),
    )
    if job is None and _report_scope(account) is None:
        job = await ReportRepository.get_report_job(report_id, None)
    if job is None:
        raise ReportNotFoundError()
    return _report_response(job)


@router.delete(
    '/{report_id}',
    response_model=ReportDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary='Delete a report status and artifact',
)
async def delete_report(
    report_id: str,
    account: Account = Depends(require_permission('report-me:delete')),
) -> ReportDeleteResponse:
    was_deleted: bool = await ReportRepository.delete_report_job(
        report_id,
        _report_scope(account),
    )
    if not was_deleted:
        raise ReportNotFoundError()
    return ReportDeleteResponse(deleted=1)


@router.get(
    '/{report_id}/download',
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary='Download a completed report artifact',
)
async def download_report(
    report_id: str,
    account: Account = Depends(require_permission('report:limited-read')),
) -> Response:
    job: ReportJob | None = await ReportRepository.get_report_job(
        report_id,
        _account_id(account),
        include_artifact=True,
    )
    if job is None:
        raise ReportNotFoundError()
    if job.status is not ReportStatus.COMPLETED:
        raise ReportNotReadyError()
    if job.artifact is None:
        raise ReportArtifactNotFoundError()
    encoded_filename: str = quote(job.file_name, safe='')
    return Response(
        content=job.artifact,
        media_type=job.content_type,
        headers={
            'Content-Disposition': (
                f'attachment; filename*=UTF-8\'\'{encoded_filename}'
            ),
        },
    )
