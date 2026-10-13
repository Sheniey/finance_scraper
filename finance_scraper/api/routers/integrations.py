import asyncio

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse
from pydantic import EmailStr

from api.exceptions.base import APIException
from api.exceptions.google import GoogleOAuthFlowError
from api.models.google import GoogleAccountConnection
from api.repositories import google as GoogleRepository
from api.schemas.google import (
    GoogleAccountStatusResponse,
    GoogleAuthorizationResponse,
    GoogleDisconnectResponse,
    GoogleFlowStatusResponse,
)
from api.services.credential_store import delete_google_refresh_token
from api.services.google_oauth import (
    build_google_callback_uri,
    complete_google_oauth,
    fail_google_oauth,
    get_google_oauth_flow,
    start_google_oauth,
)
from api.repositories import schedules as ScheduleRepository
from api.services.security import require_permission
from finance.services.account import Account


router: APIRouter = APIRouter(
    prefix='/integrations/google',
    tags=['Google integration'],
)


def _account_id(account: Account) -> str:
    return str(account.account_id or account.id)


def _callback_uri(request: Request) -> str:
    return build_google_callback_uri(
        request.url.scheme,
        request.url.hostname,
        request.url.port,
    )


def _callback_page(is_success: bool) -> HTMLResponse:
    if is_success:
        heading: str = 'Authorization complete'
        message: str = 'You can return to Finance Scraper.'
        status_code: int = status.HTTP_200_OK
    else:
        heading = 'Google could not complete authorization'
        message = 'Return to Finance Scraper and try again.'
        status_code = status.HTTP_400_BAD_REQUEST
    content: str = (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width">'
        '<meta http-equiv="Content-Security-Policy" '
        'content="default-src \'none\'; style-src \'unsafe-inline\'">'
        '<title>Finance Scraper</title>'
        '<body style="font:16px system-ui;background:#0d1726;color:#fff;'
        'padding:4rem;text-align:center">'
        f'<h1>{heading}</h1><p>{message}</p>'
        '</body></html>'
    )
    return HTMLResponse(content=content, status_code=status_code)


@router.post(
    '/authorize',
    response_model=GoogleAuthorizationResponse,
    summary='Begin a Gmail send-only OAuth authorization flow',
)
async def authorize_google_account(
    request: Request,
    account: Account = Depends(require_permission('account-me:update')),
) -> GoogleAuthorizationResponse:
    state, authorization_url = start_google_oauth(
        _account_id(account),
        _callback_uri(request),
    )
    return GoogleAuthorizationResponse(
        flow_id=state,
        authorization_url=authorization_url,
    )


@router.get(
    '/callback',
    name='google_oauth_callback',
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def google_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    if not state:
        return _callback_page(False)
    if error:
        fail_google_oauth(state, 'authorization_denied')
        return _callback_page(False)
    if not code:
        fail_google_oauth(state, 'authorization_code_missing')
        return _callback_page(False)

    try:
        await complete_google_oauth(code, state)
    except APIException:
        fail_google_oauth(state, 'authorization_exchange_failed')
        return _callback_page(False)
    return _callback_page(True)


@router.get(
    '/callback/{flow_id}',
    response_model=GoogleFlowStatusResponse,
    summary='Read the status of the authenticated account OAuth flow',
)
async def get_google_flow_status(
    flow_id: str,
    account: Account = Depends(require_permission('account-me:read')),
) -> GoogleFlowStatusResponse:
    flow = get_google_oauth_flow(_account_id(account), flow_id)
    if flow is None:
        raise GoogleOAuthFlowError()
    return GoogleFlowStatusResponse(
        status=(
            'pending'
            if flow.status == 'processing'
            else flow.status
        ),
        email=EmailStr(flow.google_email) if flow.google_email else None,
        error=flow.error,
    )


@router.get(
    '/status',
    response_model=GoogleAccountStatusResponse,
    summary='Get the current account Gmail connection metadata',
)
async def get_google_account_status(
    account: Account = Depends(require_permission('account-me:read')),
) -> GoogleAccountStatusResponse:
    connection: GoogleAccountConnection | None = (
        await GoogleRepository.get_google_connection(_account_id(account))
    )
    if connection is None:
        return GoogleAccountStatusResponse(connected=False)
    return GoogleAccountStatusResponse(
        connected=True,
        email=EmailStr(connection.google_email),
        scopes=list(connection.scopes),
    )


@router.delete(
    '/status',
    response_model=GoogleDisconnectResponse,
    summary='Disconnect the authenticated account Gmail integration',
)
async def disconnect_google_account(
    account: Account = Depends(require_permission('account-me:update')),
) -> GoogleDisconnectResponse:
    account_id: str = _account_id(account)
    disabled_schedule_ids: list[str] = (
        await ScheduleRepository.disable_account_schedules(account_id)
    )
    await asyncio.to_thread(
        delete_google_refresh_token,
        account_id,
    )
    await GoogleRepository.delete_google_connection(account_id)
    return GoogleDisconnectResponse(
        disabled_schedule_ids=disabled_schedule_ids,
    )
