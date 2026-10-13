import asyncio
import base64
import hashlib
import os
import secrets
import time
from dataclasses import dataclass
from threading import RLock
from typing import Literal
from urllib.parse import urlencode

import httpx

from api.exceptions.google import (
    GoogleOAuthFlowError,
    GoogleOAuthNotConfiguredError,
    GoogleOAuthProviderError,
)
from api.repositories import google as GoogleRepository
from api.services.credential_store import (
    get_google_refresh_token,
    store_google_refresh_token,
)


_AUTHORIZATION_ENDPOINT: str = 'https://accounts.google.com/o/oauth2/v2/auth'
_TOKEN_ENDPOINT: str = 'https://oauth2.googleapis.com/token'
_USERINFO_ENDPOINT: str = 'https://openidconnect.googleapis.com/v1/userinfo'
_GMAIL_SCOPE: str = 'https://www.googleapis.com/auth/gmail.send'
_GMAIL_SCOPES: tuple[str, ...] = ('openid', 'email', _GMAIL_SCOPE)
_LOGIN_SCOPES: tuple[str, ...] = ('openid', 'email', 'profile')
_GOOGLE_EMAIL_SCOPE_ALIASES: frozenset[str] = frozenset(
    {'email', 'https://www.googleapis.com/auth/userinfo.email'},
)
_FLOW_TTL_SECONDS: int = 600
_FLOW_RESULT_TTL_SECONDS: int = 900


@dataclass(frozen=True, slots=True)
class GoogleLoginIdentity:
    email: str
    name: str | None


@dataclass(slots=True)
class PendingGoogleFlow:
    account_id: str | None
    redirect_uri: str
    code_verifier: str
    created_at: int
    state: str
    purpose: Literal['gmail', 'login'] = 'gmail'
    status: Literal['pending', 'processing', 'completed', 'failed'] = 'pending'
    google_email: str | None = None
    google_name: str | None = None
    error: str | None = None
    finished_at: int | None = None


_pending_flows: dict[str, PendingGoogleFlow] = {}
_pending_flows_lock: RLock = RLock()


def _google_client_id() -> str:
    client_id: str = (os.getenv('GOOGLE_OAUTH_CLIENT_ID') or '').strip()
    if not client_id:
        raise GoogleOAuthNotConfiguredError()
    return client_id


def build_google_callback_uri(
    scheme: str,
    hostname: str | None,
    port: int | None,
) -> str:
    if scheme != 'http' or hostname not in {'127.0.0.1', 'localhost', '::1'}:
        raise GoogleOAuthFlowError(
            'Google OAuth callbacks must use a local loopback address',
        )
    if port is None:
        raise GoogleOAuthFlowError(
            'Google OAuth callback requires a local API port',
        )
    return f'http://127.0.0.1:{port}/integrations/google/callback'


def _authorization_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_verifier: str,
    scopes: tuple[str, ...],
    prompt: str,
) -> str:
    code_challenge: str = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('ascii')).digest(),
    ).decode('ascii').rstrip('=')
    query: str = urlencode(
        {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(scopes),
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'include_granted_scopes': 'false',
            'prompt': prompt,
        },
    )
    if prompt == 'consent':
        query += '&access_type=offline'
    return f'{_AUTHORIZATION_ENDPOINT}?{query}'


def _has_required_scopes(
    granted_scopes: str | None,
    purpose: Literal['gmail', 'login'],
) -> bool:
    if not granted_scopes:
        return False
    scopes: set[str] = set(granted_scopes.split())
    if purpose == 'gmail':
        return _GMAIL_SCOPE in scopes
    return 'openid' in scopes and bool(
        scopes & _GOOGLE_EMAIL_SCOPE_ALIASES,
    )


def _remove_expired_flows(now: int) -> None:
    expired_states: list[str] = [
        state
        for state, flow in _pending_flows.items()
        if (
            flow.status in {'pending', 'processing'}
            and now - flow.created_at > _FLOW_TTL_SECONDS
        )
        or (
            flow.status != 'pending'
            and flow.finished_at is not None
            and now - flow.finished_at > _FLOW_RESULT_TTL_SECONDS
        )
    ]
    for state in expired_states:
        _pending_flows.pop(state, None)


def _start_google_flow(
    account_id: str | None,
    redirect_uri: str,
    purpose: Literal['gmail', 'login'],
    scopes: tuple[str, ...],
    prompt: str,
) -> tuple[str, str]:
    client_id: str = _google_client_id()
    created_at: int = int(time.time())
    state: str = secrets.token_urlsafe(32)
    code_verifier: str = secrets.token_urlsafe(64)
    flow: PendingGoogleFlow = PendingGoogleFlow(
        account_id=account_id,
        redirect_uri=redirect_uri,
        code_verifier=code_verifier,
        created_at=created_at,
        state=state,
        purpose=purpose,
    )
    with _pending_flows_lock:
        _remove_expired_flows(created_at)
        _pending_flows[state] = flow

    return state, _authorization_url(
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=state,
        code_verifier=code_verifier,
        scopes=scopes,
        prompt=prompt,
    )


def start_google_oauth(
    account_id: str,
    redirect_uri: str,
) -> tuple[str, str]:
    return _start_google_flow(
        account_id,
        redirect_uri,
        'gmail',
        _GMAIL_SCOPES,
        'consent',
    )


def start_google_login(redirect_uri: str) -> tuple[str, str]:
    return _start_google_flow(
        None,
        redirect_uri,
        'login',
        _LOGIN_SCOPES,
        'select_account',
    )


def fail_google_oauth(state: str, reason: str) -> bool:
    with _pending_flows_lock:
        flow: PendingGoogleFlow | None = _pending_flows.get(state)
        if flow is None or flow.status not in {'pending', 'processing'}:
            return False
        flow.status = 'failed'
        flow.error = reason[:128]
        flow.finished_at = int(time.time())
    return True


def get_google_oauth_flow(
    account_id: str,
    state: str,
) -> PendingGoogleFlow | None:
    now: int = int(time.time())
    with _pending_flows_lock:
        _remove_expired_flows(now)
        flow: PendingGoogleFlow | None = _pending_flows.get(state)
        if (
            flow is None
            or flow.purpose != 'gmail'
            or flow.account_id != account_id
        ):
            return None
        return flow


def get_google_login_flow(state: str) -> PendingGoogleFlow | None:
    now: int = int(time.time())
    with _pending_flows_lock:
        _remove_expired_flows(now)
        flow: PendingGoogleFlow | None = _pending_flows.get(state)
        if flow is None or flow.purpose != 'login':
            return None
        return flow


def consume_google_login_flow(state: str) -> GoogleLoginIdentity | None:
    now: int = int(time.time())
    with _pending_flows_lock:
        _remove_expired_flows(now)
        flow: PendingGoogleFlow | None = _pending_flows.get(state)
        if (
            flow is None
            or flow.purpose != 'login'
            or flow.status != 'completed'
            or flow.google_email is None
        ):
            return None
        _pending_flows.pop(state, None)
        if flow.finished_at is None or now - flow.finished_at > _FLOW_RESULT_TTL_SECONDS:
            return None
        return GoogleLoginIdentity(
            email=flow.google_email,
            name=flow.google_name,
        )


async def complete_google_oauth(
    code: str,
    state: str,
) -> str:
    with _pending_flows_lock:
        flow: PendingGoogleFlow | None = _pending_flows.get(state)
        if (
            flow is None
            or flow.status != 'pending'
            or int(time.time()) - flow.created_at > _FLOW_TTL_SECONDS
        ):
            raise GoogleOAuthFlowError()
        flow.status = 'processing'
        pending_flow: PendingGoogleFlow = flow

    client_id: str = _google_client_id()
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            token_response = await client.post(
                _TOKEN_ENDPOINT,
                data={
                    'client_id': client_id,
                    'code': code,
                    'code_verifier': pending_flow.code_verifier,
                    'grant_type': 'authorization_code',
                    'redirect_uri': pending_flow.redirect_uri,
                },
            )
            token_response.raise_for_status()
            token_data: object = token_response.json()
            if not isinstance(token_data, dict):
                raise GoogleOAuthProviderError()
            access_token: object = token_data.get('access_token')
            if not isinstance(access_token, str) or not access_token:
                raise GoogleOAuthProviderError()
            granted_scopes: object = token_data.get('scope')
            if (
                not isinstance(granted_scopes, str)
                or not _has_required_scopes(
                    granted_scopes,
                    pending_flow.purpose,
                )
            ):
                raise GoogleOAuthProviderError(
                    'Google did not grant the required sign-in permissions',
                )

            userinfo_response = await client.get(
                _USERINFO_ENDPOINT,
                headers={'Authorization': f'Bearer {access_token}'},
            )
            userinfo_response.raise_for_status()
            userinfo: object = userinfo_response.json()
    except (httpx.HTTPError, ValueError) as e:
        raise GoogleOAuthProviderError() from e

    if not isinstance(userinfo, dict):
        raise GoogleOAuthProviderError()
    google_email: object = userinfo.get('email')
    email_verified: object = userinfo.get('email_verified')
    if (
        not isinstance(google_email, str)
        or not google_email
        or email_verified is not True
    ):
        raise GoogleOAuthProviderError(
            'Google did not return a verified email address',
        )

    if pending_flow.purpose == 'login':
        google_subject: object = userinfo.get('sub')
        google_name: object = userinfo.get('name')
        if not isinstance(google_subject, str) or not google_subject:
            raise GoogleOAuthProviderError(
                'Google did not return a verified account identifier',
            )
        with _pending_flows_lock:
            stored_flow: PendingGoogleFlow | None = _pending_flows.get(state)
            if stored_flow is None or stored_flow.status != 'processing':
                raise GoogleOAuthFlowError()
            stored_flow.status = 'completed'
            stored_flow.google_email = google_email.strip().casefold()
            stored_flow.google_name = (
                google_name.strip()
                if isinstance(google_name, str) and google_name.strip()
                else None
            )
            stored_flow.error = None
            stored_flow.finished_at = int(time.time())
        return google_email.strip().casefold()

    if pending_flow.account_id is None:
        raise GoogleOAuthFlowError()

    refresh_token: object = token_data.get('refresh_token')
    if not isinstance(refresh_token, str) or not refresh_token:
        refresh_token = await asyncio.to_thread(
            get_google_refresh_token,
            pending_flow.account_id,
        )
    if not isinstance(refresh_token, str) or not refresh_token:
        raise GoogleOAuthProviderError(
            'Google did not return a refresh token; reconnect and approve offline access',
        )

    await asyncio.to_thread(
        store_google_refresh_token,
        pending_flow.account_id,
        refresh_token,
    )
    connection = await GoogleRepository.save_google_connection(
        pending_flow.account_id,
        google_email,
        _GMAIL_SCOPES,
    )

    with _pending_flows_lock:
        stored_flow: PendingGoogleFlow | None = _pending_flows.get(state)
        if stored_flow is not None and stored_flow.status == 'processing':
            stored_flow.status = 'completed'
            stored_flow.google_email = connection.google_email
            stored_flow.error = None
            stored_flow.finished_at = int(time.time())
    return connection.google_email
