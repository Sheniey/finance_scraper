
import hashlib, binascii, base64
import hmac, json, time
from typing import Any
from uuid import uuid4
from designkit.structural.environment import EnvMode

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from finance.services.account import Account, get_by_email, get_by_id

from api.core.config import (
    envm, settings,
    DEFAULT_JWT_SECRET_KEY,
    JWT_ALGORITHM,
    JWT_ISSUER,
    JWT_SECRET_KEY,
)
from api.exceptions.auth import IncorrectCredentialsError, InvalidExpiredTokenError
from api.models.auth import TokenClaims
from api.repositories import auth as AuthRepository
from api.schemas.auth import TokenPairResponse


if (
    envm.environment == EnvMode.PRODUCTION
    and (
        not JWT_SECRET_KEY
        or JWT_SECRET_KEY == DEFAULT_JWT_SECRET_KEY
    )
):
    raise RuntimeError('JWT_SECRET_KEY must be configured in production')
if JWT_ALGORITHM != 'HS256':
    raise RuntimeError('The API currently supports only HS256 JWTs')

bearer_scheme: HTTPBearer = HTTPBearer(
    scheme_name='BearerAuth',
    auto_error=False,
)


def _encode_part(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode('ascii')

def _decode_part(value: str) -> bytes:
    if not value or any(
        character not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        'abcdefghijklmnopqrstuvwxyz0123456789-_'
        for character in value
    ):
        raise ValueError('JWT contains an invalid base64 segment')
    return base64.urlsafe_b64decode(
        value + '=' * (-len(value) % 4),
    )


def create_token(claims: TokenClaims, email: str) -> str:
    header: dict[str, str] = {'alg': 'HS256', 'typ': 'JWT'}
    payload: dict[str, Any] = {
        'sub': claims.account_id,
        'email': email,
        'sid': claims.session_id,
        'jti': claims.token_id,
        'typ': claims.token_type,
        'iat': claims.issued_at,
        'exp': claims.expires_at,
        'iss': JWT_ISSUER,
    }
    encoded_header: str = _encode_part(
        json.dumps(header, separators=(',', ':')).encode('utf-8'),
    )
    encoded_payload: str = _encode_part(
        json.dumps(payload, separators=(',', ':')).encode('utf-8'),
    )
    signing_input: bytes = f'{encoded_header}.{encoded_payload}'.encode('ascii')
    signature: bytes = hmac.new(
        JWT_SECRET_KEY.encode('utf-8'),
        signing_input,
        hashlib.sha256,
    ).digest()
    return (
        f'{encoded_header}.{encoded_payload}.{_encode_part(signature)}'
    )

def decode_token(token: str) -> TokenClaims:
    try:
        parts: list[str] = token.split('.')
        if len(parts) != 3:
            raise ValueError('Invalid JWT format')
        encoded_header, encoded_payload, encoded_signature = parts
        signing_input: bytes = (
            f'{encoded_header}.{encoded_payload}'.encode('ascii')
        )
        expected_signature: bytes = hmac.new(
            JWT_SECRET_KEY.encode('utf-8'),
            signing_input,
            hashlib.sha256,
        ).digest()
        signature: bytes = _decode_part(encoded_signature)
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError('Invalid JWT signature')

        header: Any = json.loads(_decode_part(encoded_header))
        payload: Any = json.loads(_decode_part(encoded_payload))
    except (
        UnicodeError,
        binascii.Error,
        json.JSONDecodeError,
        TypeError,
    ) as e:
        raise ValueError('Invalid JWT encoding') from e

    if (
        not isinstance(header, dict)
        or header.get('alg') != 'HS256'
        or header.get('typ') != 'JWT'
        or not isinstance(payload, dict)
    ):
        raise ValueError('Invalid JWT header or payload')

    account_id: Any = payload.get('sub')
    session_id: Any = payload.get('sid')
    token_id: Any = payload.get('jti')
    token_type: Any = payload.get('typ')
    issued_at: Any = payload.get('iat')
    expires_at: Any = payload.get('exp')
    now: int = int(time.time())
    if (
        not isinstance(account_id, str)
        or not isinstance(session_id, str)
        or not isinstance(token_id, str)
        or not isinstance(token_type, str)
        or token_type not in {'access', 'refresh'}
        or type(issued_at) is not int
        or type(expires_at) is not int
        or payload.get('iss') != JWT_ISSUER
        or not isinstance(payload.get('email'), str)
        or expires_at <= now
        or issued_at > now + 60
    ):
        raise ValueError('JWT claims are invalid or expired')

    return TokenClaims(
        account_id=account_id,
        session_id=session_id,
        token_id=token_id,
        token_type=token_type,
        issued_at=issued_at,
        expires_at=expires_at,
    )


async def authenticate(email: str, password: str) -> Account | None:
    account: Account | None = await get_by_email(email, password)
    return account


async def issue_token_pair(account: Account) -> TokenPairResponse:
    issued_at: int = int(time.time())
    access_expires_at: int = (
        issued_at + settings.security.access_token_expire_minutes * 60
    )
    refresh_expires_at: int = (
        issued_at + settings.security.refresh_token_expire_days * 24 * 60 * 60
    )
    account_id: str = str(account.account_id or account.id)
    session_id: str = uuid4().hex
    access_claims: TokenClaims = TokenClaims(
        account_id=account_id,
        session_id=session_id,
        token_id=uuid4().hex,
        token_type='access',
        issued_at=issued_at,
        expires_at=access_expires_at,
    )
    refresh_claims: TokenClaims = TokenClaims(
        account_id=account_id,
        session_id=session_id,
        token_id=uuid4().hex,
        token_type='refresh',
        issued_at=issued_at,
        expires_at=refresh_expires_at,
    )
    await AuthRepository.store_token_pair(
        session_id=session_id,
        account_id=account_id,
        access_jti=access_claims.token_id,
        access_expires_at=access_expires_at,
        refresh_jti=refresh_claims.token_id,
        refresh_expires_at=refresh_expires_at,
        issued_at=issued_at,
    )
    return TokenPairResponse(
        access_token=create_token(access_claims, str(account.email)),
        refresh_token=create_token(refresh_claims, str(account.email)),
        expires_in=access_expires_at - issued_at,
        refresh_expires_in=refresh_expires_at - issued_at,
    )


async def refresh_token_pair(refresh_token: str) -> TokenPairResponse:
    try:
        old_claims: TokenClaims = decode_token(refresh_token)
    except ValueError as e:
        raise InvalidExpiredTokenError() from e
    if old_claims.token_type != 'refresh':
        raise InvalidExpiredTokenError()

    account: Account | None = await get_by_id(old_claims.account_id)
    if account is None:
        raise InvalidExpiredTokenError()

    issued_at: int = int(time.time())
    access_expires_at: int = (
        issued_at + settings.security.access_token_expire_minutes * 60
    )
    refresh_expires_at: int = (
        issued_at + settings.security.refresh_token_expire_days * 24 * 60 * 60
    )
    access_claims: TokenClaims = TokenClaims(
        account_id=old_claims.account_id,
        session_id=old_claims.session_id,
        token_id=uuid4().hex,
        token_type='access',
        issued_at=issued_at,
        expires_at=access_expires_at,
    )
    new_refresh_claims: TokenClaims = TokenClaims(
        account_id=old_claims.account_id,
        session_id=old_claims.session_id,
        token_id=uuid4().hex,
        token_type='refresh',
        issued_at=issued_at,
        expires_at=refresh_expires_at,
    )
    was_rotated: bool = await AuthRepository.rotate_refresh_token(
        old_refresh_jti=old_claims.token_id,
        session_id=old_claims.session_id,
        account_id=old_claims.account_id,
        new_access_jti=access_claims.token_id,
        access_expires_at=access_expires_at,
        new_refresh_jti=new_refresh_claims.token_id,
        refresh_expires_at=refresh_expires_at,
        issued_at=issued_at,
    )
    if not was_rotated:
        raise InvalidExpiredTokenError()
    return TokenPairResponse(
        access_token=create_token(access_claims, str(account.email)),
        refresh_token=create_token(new_refresh_claims, str(account.email)),
        expires_in=access_expires_at - issued_at,
        refresh_expires_in=refresh_expires_at - issued_at,
    )


async def get_account_and_claims(token: str) -> tuple[Account, TokenClaims]:
    try:
        claims: TokenClaims = decode_token(token)
    except ValueError as e:
        raise InvalidExpiredTokenError() from e
    if claims.token_type != 'access':
        raise InvalidExpiredTokenError()

    is_active: bool = await AuthRepository.is_token_active(
        token_id=claims.token_id,
        session_id=claims.session_id,
        account_id=claims.account_id,
        token_type='access',
    )
    if not is_active:
        raise InvalidExpiredTokenError()

    account: Account | None = await get_by_id(claims.account_id)
    if account is None:
        raise InvalidExpiredTokenError()
    return account, claims


async def get_account_from_token(token: str) -> Account:
    account, _ = await get_account_and_claims(token)
    return account


async def get_current_account(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Account:
    if credentials is None:
        raise InvalidExpiredTokenError()
    account, claims = await get_account_and_claims(credentials.credentials)
    request.state.authenticated_account_id = str(
        account.account_id or account.id,
    )
    request.state.token_claims = claims
    return account
