import secrets

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import SecretStr

from api.services.security import require_permission
from finance.services.account import Account
from finance.services.account.exceptions import (
    AccountAlreadyExistsError as FinanceAccountAlreadyExistsError,
)
from slowapi.util import get_remote_address

from api.core.config import settings
from api.core.desktop import require_desktop_control_token
from api.core.security import (
    authenticate,
    issue_token_pair,
    refresh_token_pair,
)
from api.exceptions.account import AccountAlreadyExistsError
from api.exceptions.auth import IncorrectCredentialsError
from api.exceptions.google import GoogleOAuthFlowError
from api.repositories import account as AccountRepository
from api.models.auth import TokenClaims
from api.schemas.auth import (
    GoogleLoginFlowRequest,
    GoogleLoginFlowResponse,
    LoginRequest,
    LogoutResponse,
    RegistrationRequest,
    RefreshRequest,
    TokenPairResponse,
)
from api.schemas.account import AccountResponse
from api.services.auth_sessions import invalidate_tokens
from api.schemas.google import GoogleAuthorizationResponse
from api.services.google_oauth import (
    build_google_callback_uri,
    consume_google_login_flow,
    get_google_login_flow,
    start_google_login,
)
from api.services.rate_limit import limiter


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
    except FinanceAccountAlreadyExistsError as e:
        raise AccountAlreadyExistsError() from e
    return AccountResponse.from_account(account)


@router.post(
    '/google/authorize',
    response_model=GoogleAuthorizationResponse,
    summary='Begin a Google sign-in flow for the desktop app',
)
@limiter.limit(
    f'{settings.security.rate_limits.login_per_minute}/minute',
    key_func=get_remote_address,
)
async def authorize_google_signin(
    request: Request,
    response: Response,
    _: None = Depends(require_desktop_control_token),
) -> GoogleAuthorizationResponse:
    flow_id, authorization_url = start_google_login(
        build_google_callback_uri(
            request.url.scheme,
            request.url.hostname,
            request.url.port,
        ),
    )
    return GoogleAuthorizationResponse(
        flow_id=flow_id,
        authorization_url=authorization_url,
    )


@router.get(
    '/google/flow/{flow_id}',
    response_model=GoogleLoginFlowResponse,
    summary='Read a desktop Google sign-in flow status',
)
async def get_google_signin_flow(
    flow_id: str,
    _: None = Depends(require_desktop_control_token),
) -> GoogleLoginFlowResponse:
    flow = get_google_login_flow(flow_id)
    if flow is None:
        raise GoogleOAuthFlowError()
    flow_status = 'pending' if flow.status == 'processing' else flow.status
    return GoogleLoginFlowResponse(
        status=flow_status,
        email=EmailStr(flow.google_email) if flow.google_email else None,
        name=flow.google_name,
        error=flow.error,
    )


@router.post(
    '/google/login',
    response_model=TokenPairResponse,
    summary='Sign in or create a local profile from a verified Google identity',
)
@limiter.limit(
    f'{settings.security.rate_limits.login_per_minute}/minute',
    key_func=get_remote_address,
)
async def login_with_google(
    request: Request,
    response: Response,
    payload: GoogleLoginFlowRequest,
    _: None = Depends(require_desktop_control_token),
) -> TokenPairResponse:
    identity = consume_google_login_flow(payload.flow_id)
    if identity is None:
        raise GoogleOAuthFlowError()

    email = identity.email.casefold()
    account = await AccountRepository.get_account_by_email(email)
    if account is None:
        name = ' '.join(
            (identity.name or email.split('@', maxsplit=1)[0]).split(),
        )
        if not name:
            name = email.split('@', maxsplit=1)[0]
        registration = RegistrationRequest(
            name=name[:120],
            email=email,
            password=SecretStr(secrets.token_urlsafe(48)),
        )
        try:
            account = await AccountRepository.create_account(registration)
        except FinanceAccountAlreadyExistsError:
            account = await AccountRepository.get_account_by_email(email)
            if account is None:
                raise AccountAlreadyExistsError() from None
    if account is None:
        raise GoogleOAuthFlowError('The Google profile could not be created.')

    return await issue_token_pair(account)


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
    account: Account | None = await authenticate(
        str(payload.email),
        payload.password.get_secret_value(),
    )
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
