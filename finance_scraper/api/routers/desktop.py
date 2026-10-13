import os

from fastapi import APIRouter, Depends, Request

from api.core.desktop import require_desktop_control_token
from api.exceptions.security import DesktopServerControlUnavailableError
from api.schemas.base import OKResponse
from api.services.worker_capacity import get_report_worker_concurrency


router: APIRouter = APIRouter(prefix='/desktop', tags=['desktop lifecycle'])


class DesktopHealthResponse(OKResponse):
    process_id: int
    report_worker_max_concurrency: int


@router.get(
    '/health',
    response_model=DesktopHealthResponse,
    summary='Verify the local desktop API process',
)
async def health(
    _: None = Depends(require_desktop_control_token),
) -> DesktopHealthResponse:
    return DesktopHealthResponse(
        process_id=os.getpid(),
        report_worker_max_concurrency=(
            get_report_worker_concurrency()
        ),
    )


@router.post(
    '/shutdown',
    response_model=OKResponse,
    summary='Gracefully stop the desktop-managed API process',
)
async def shutdown(
    request: Request,
    _: None = Depends(require_desktop_control_token),
) -> OKResponse:
    server = getattr(request.app.state, 'uvicorn_server', None)
    if server is None:
        raise DesktopServerControlUnavailableError()
    server.should_exit = True
    return OKResponse()
