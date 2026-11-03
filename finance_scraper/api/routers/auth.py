from fastapi import APIRouter, Depends, Request, Response, status
from slowapi.util import get_remote_address

from api.core.config import settings
from api.core.desktop import require_desktop_control_token
from api.core.security import authenticate, issue_token_pair, refresh_token_pair
from api.exceptions.account import (
    AccountAlreadyExistsError,
    AccountVaultUnavailableError,
)
from api.exceptions.auth import IncorrectCredentialsError
from api.models.auth import TokenClaims
from api.repositories import account as AccountRepository
from api.schemas.account import AccountResponse
from api.schemas.auth import (
    LoginRequest,
    LogoutResponse,
    RefreshRequest,
    RegistrationRequest,
    TokenPairResponse,
)
from api.services.auth_sessions import invalidate_tokens
from api.services.rate_limit import limiter
from api.services.security import require_permission
from finance.services.account import (
    Account,
    AccountAlreadyExistsError as FinanceAccountAlreadyExistsError,
    AccountVaultException,
    vault_sessions,
)


router: APIRouter = APIRouter(prefix='/auth', tags=['authentication'])


@router.post(
    '/register',
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Register a local Finance Scraper account from the desktop app',
)
@limiter.limit(
    f'{settings.security.rate_limits.register_per_minute}/minute',
    key_func=get_remote_address,
)
async def register(
    request: Request,
    response: Response,
    payload: RegistrationRequest,
    _: None = Depends(require_desktop_control_token),
) -> AccountResponse:
    try:
        account: Account = await AccountRepository.create_account(payload)
    except FinanceAccountAlreadyExistsError as error:
        raise AccountAlreadyExistsError() from error
    return AccountResponse.from_account(account)


@router.post(
    '/login',
    response_model=TokenPairResponse,
    status_code=status.HTTP_200_OK,
    summary='Authenticate an account and issue access and refresh tokens',
)
@limiter.limit(
    f'{settings.security.rate_limits.login_per_minute}/minute',
    key_func=get_remote_address,
)
async def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
) -> TokenPairResponse:
    try:
        account: Account | None = await authenticate(
            str(payload.email),
            payload.password.get_secret_value(),
        )
    except AccountVaultException as error:
        raise AccountVaultUnavailableError() from error
    if account is None:
        raise IncorrectCredentialsError()
    return await issue_token_pair(account)


@router.post(
    '/logout',
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary='Invalidate the authenticated access and refresh tokens',
)
async def logout(
    request: Request,
    account: Account = Depends(require_permission('auth:logout')),
) -> LogoutResponse:
    claims: TokenClaims = request.state.token_claims
    await invalidate_tokens(session_id=claims.session_id)
    vault_sessions.lock(account.account_id or account.id)
    return LogoutResponse()


@router.post(
    '/refresh',
    response_model=TokenPairResponse,
    status_code=status.HTTP_200_OK,
    summary='Rotate a refresh token and issue a new token pair',
)
async def refresh(
    payload: RefreshRequest,
) -> TokenPairResponse:
    return await refresh_token_pair(
        payload.refresh_token.get_secret_value(),
    )
