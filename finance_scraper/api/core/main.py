
import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from finance.config import (
    DB_AUTH_TOKEN,
    DB_LOCAL_PATH,
    DB_LOCATION,
    DB_POOL_SIZE,
    DB_POOL_TIMEOUT,
    DESKTOP_LOCAL_ONLY,
)
from finance.services.account.db import initialize_account_database
from finance.services.database import (
    AsyncClientPool,
    DatabaseSyncError,
    close_database_pools,
    get_database_pool,
    get_turso_sync_pool,
)
from finance.services.database.synchronization import run_sync_worker

from finance.services.report_store.reports import initialize_report_store
from finance.services.report_store.database import report_database
from api.core.config import API_TITLE, API_VERSION, DESCRIPTION, settings
from api.core.database import initialize_api_database
from api.exceptions.base import APIException
from api.middlewares.request_context import RequestContextMiddleware
from api.routers.accounts import router as accounts_router
from api.routers.auth import router as auth_router
from api.routers.desktop import router as desktop_router
from api.routers.integrations import router as integrations_router
from api.routers.reports import router as reports_router
from api.routers.schedules import router as schedules_router
from api.repositories import report as ReportRepository
from api.schemas.base import ErrorResponse
from api.services.rate_limit import limiter
from api.services.report_migration import migrate_legacy_report_databases
from api.services.report_worker import run_report_worker


logger: logging.Logger = logging.getLogger(__name__)
if (
    os.getenv('FINANCE_DESKTOP_LOCAL_ONLY', '').casefold()
    in {'1', 'true', 'yes', 'on'}
    and not DESKTOP_LOCAL_ONLY
):
    raise RuntimeError(
        'FINANCE_DESKTOP_LOCAL_ONLY was requested but finance.config did not apply it',
    )


async def _rate_limit_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        headers={'Retry-After': '60'},
        content=ErrorResponse(
            error='RATE_LIMIT_EXCEEDED',
            message='Too many requests; try again later',
            status_code=429,
        ).model_dump(),
    )

async def _request_validation_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    details: list[str] = [
        f'{".".join(str(part) for part in error["loc"])}: {error["msg"]}'
        for error in exc.errors()
    ]
    message: str = '; '.join(details)[:256] or 'Request validation failed'
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error='INVALID_REQUEST',
            message=message,
            status_code=422,
        ).model_dump(),
    )

@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    stop_event: asyncio.Event = asyncio.Event()
    report_worker_task: asyncio.Task[None] | None = None
    sync_worker_task: asyncio.Task[None] | None = None
    sync_pool: AsyncClientPool | None = None
    logger.info(
        'Desktop local-only mode: %s; remote synchronization enabled: %s',
        DESKTOP_LOCAL_ONLY,
        bool(DB_LOCATION),
    )
    try:
        if DB_LOCATION and not DESKTOP_LOCAL_ONLY:
            sync_pool = await get_turso_sync_pool(
                DB_LOCAL_PATH,
                remote_url=DB_LOCATION,
                auth_token=DB_AUTH_TOKEN,
                size=DB_POOL_SIZE,
                acquire_timeout=DB_POOL_TIMEOUT,
            )
        else:
            sync_pool = await get_database_pool(
                DB_LOCAL_PATH,
                auth_token=None,
                size=DB_POOL_SIZE,
                acquire_timeout=DB_POOL_TIMEOUT,
            )
        await initialize_account_database()
        await asyncio.to_thread(migrate_legacy_report_databases)
        await asyncio.to_thread(initialize_report_store)
        await ReportRepository.apply_report_retention(
            settings.api.report_retention_seconds,
        )
        await initialize_api_database()
        if DB_LOCATION and not DESKTOP_LOCAL_ONLY:
            sync_worker_task = asyncio.create_task(
                run_sync_worker(sync_pool, stop_event),
                name='api-turso-sync-worker',
            )
        report_worker_task = asyncio.create_task(
            run_report_worker(stop_event),
            name='api-report-worker',
        )
        application.state.sync_worker_task = sync_worker_task
        application.state.report_worker_task = report_worker_task
        yield
    finally:
        stop_event.set()
        try:
            if report_worker_task is not None:
                report_worker_task.cancel()
                try:
                    await report_worker_task
                except asyncio.CancelledError:
                    pass
        finally:
            if sync_worker_task is not None:
                await sync_worker_task
            if sync_pool is not None and sync_pool.is_turso_sync:
                try:
                    await sync_pool.push()
                except DatabaseSyncError as e:
                    logger.warning(
                        'Final Turso push failed; pending changes remain local: %s',
                        e,
                    )
            try:
                report_database.close()
            finally:
                await close_database_pools()


app: FastAPI = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=DESCRIPTION,
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_exception_handler(APIException, APIException.handler)
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
app.add_exception_handler(
    RequestValidationError,
    _request_validation_handler,
)
app.include_router(auth_router)
app.include_router(accounts_router)
app.include_router(desktop_router)
app.include_router(integrations_router)
app.include_router(reports_router)
app.include_router(schedules_router)
