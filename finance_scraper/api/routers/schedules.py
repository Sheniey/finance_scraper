from fastapi import APIRouter, Depends, Request, Response, status

from api.core.config import settings
from api.core.desktop import require_desktop_control_token
from api.exceptions.google import GoogleAccountNotConnectedError
from api.exceptions.schedule import (
    ScheduleLimitExceededError,
    ScheduleNotFoundError,
)
from api.models.report import ReportFormat
from api.models.schedule import ReportSchedule, ScheduleRunResult
from api.repositories import google as GoogleRepository
from api.repositories import schedules as ScheduleRepository
from api.schemas.base import OKResponse
from api.schemas.schedule import (
    ScheduleCreate,
    ScheduleListResponse,
    ScheduleResponse,
    ScheduleRunBatchResponse,
    ScheduleRunResponse,
    ScheduleTaskRegistryResponse,
    ScheduleTaskResponse,
    ScheduleUpdate,
)
from api.services.rate_limit import limiter
from api.services.schedules import (
    run_due_scheduled_reports,
    run_scheduled_report,
)
from api.services.security import require_permission
from finance.services.account import Account
from finance.types.report_mode import ReportMode


router: APIRouter = APIRouter(prefix='/schedules', tags=['scheduled reports'])
_MAX_SCHEDULES_PER_ACCOUNT: int = 20


def _account_id(account: Account) -> str:
    return str(account.account_id or account.id)


def _schedule_response(schedule: ReportSchedule) -> ScheduleResponse:
    return ScheduleResponse(
        schedule_id=schedule.schedule_id,
        tickers=list(schedule.tickers),
        report_format=ReportFormat(schedule.report_format),
        run_at=schedule.run_at,
        timezone=schedule.timezone,
        explain=schedule.explain,
        mode=ReportMode(schedule.mode),
        charts=schedule.charts,
        ml_horizon=schedule.ml_horizon,
        enabled=schedule.enabled,
        last_run_date=schedule.last_run_date,
        last_run_status=schedule.last_run_status,
        last_error=schedule.last_error,
    )


def _schedule_run_response(result: ScheduleRunResult) -> ScheduleRunResponse:
    return ScheduleRunResponse(
        schedule_id=result.schedule_id,
        scheduled_date=result.scheduled_date,
        status=result.status,
        report_ids=list(result.report_ids),
    )


@router.get(
    '/me',
    response_model=ScheduleListResponse,
    summary='List the authenticated account report schedules',
)
async def get_my_schedules(
    account: Account = Depends(require_permission('account-me:read')),
) -> ScheduleListResponse:
    schedules: list[ReportSchedule] = (
        await ScheduleRepository.list_schedules(_account_id(account))
    )
    return ScheduleListResponse(
        schedules=[
            _schedule_response(schedule)
            for schedule in schedules
        ],
    )


@router.post(
    '/me',
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Create a daily report schedule for the authenticated account',
)
@limiter.limit(f'{settings.security.rate_limits.default_per_minute}/minute')
async def create_my_schedule(
    request: Request,
    response: Response,
    payload: ScheduleCreate,
    account: Account = Depends(require_permission('report:create')),
) -> ScheduleResponse:
    account_id: str = _account_id(account)
    if await GoogleRepository.get_google_connection(account_id) is None:
        raise GoogleAccountNotConnectedError()
    if (
        await ScheduleRepository.count_schedules(account_id)
        >= _MAX_SCHEDULES_PER_ACCOUNT
    ):
        raise ScheduleLimitExceededError()
    schedule: ReportSchedule = await ScheduleRepository.create_schedule(
        account_id,
        payload,
    )
    return _schedule_response(schedule)


@router.patch(
    '/me/{schedule_id}',
    response_model=ScheduleResponse,
    summary='Enable or pause an owned report schedule',
)
async def update_my_schedule(
    schedule_id: str,
    payload: ScheduleUpdate,
    account: Account = Depends(require_permission('account-me:update')),
) -> ScheduleResponse:
    schedule: ReportSchedule | None = (
        await ScheduleRepository.set_schedule_enabled(
            schedule_id,
            _account_id(account),
            payload.enabled,
        )
    )
    if schedule is None:
        raise ScheduleNotFoundError()
    return _schedule_response(schedule)


@router.delete(
    '/me/{schedule_id}',
    response_model=OKResponse,
    summary='Delete an owned report schedule and its run records',
)
async def delete_my_schedule(
    schedule_id: str,
    account: Account = Depends(require_permission('account-me:update')),
) -> OKResponse:
    was_deleted: bool = await ScheduleRepository.delete_schedule(
        schedule_id,
        _account_id(account),
    )
    if not was_deleted:
        raise ScheduleNotFoundError()
    return OKResponse()


@router.post(
    '/desktop/{schedule_id}/run',
    response_model=ScheduleRunResponse,
    summary='Run a due report schedule from the desktop helper',
)
async def run_desktop_schedule(
    schedule_id: str,
    _: None = Depends(require_desktop_control_token),
) -> ScheduleRunResponse:
    result: ScheduleRunResult = await run_scheduled_report(schedule_id)
    return _schedule_run_response(result)


@router.post(
    '/desktop/run-due',
    response_model=ScheduleRunBatchResponse,
    summary='Recover due report schedules after device downtime',
)
async def recover_desktop_schedules(
    _: None = Depends(require_desktop_control_token),
) -> ScheduleRunBatchResponse:
    results: list[ScheduleRunResult] = await run_due_scheduled_reports()
    return ScheduleRunBatchResponse(
        runs=[
            _schedule_run_response(result)
            for result in results
        ],
    )


@router.get(
    '/desktop/registry',
    response_model=ScheduleTaskRegistryResponse,
    summary='Read task registration metadata for the local desktop helper',
)
async def get_desktop_schedule_registry(
    _: None = Depends(require_desktop_control_token),
) -> ScheduleTaskRegistryResponse:
    schedules: list[ReportSchedule] = (
        await ScheduleRepository.list_all_schedules()
    )
    return ScheduleTaskRegistryResponse(
        schedules=[
            ScheduleTaskResponse(
                schedule_id=schedule.schedule_id,
                run_at=schedule.run_at,
                enabled=schedule.enabled,
            )
            for schedule in schedules
        ],
    )
