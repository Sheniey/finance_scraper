import asyncio
from urllib.parse import parse_qs, urlparse
from urllib.parse import parse_qs as parse_form
from urllib.parse import urlparse as parse_url

from fastapi.testclient import TestClient
import httpx

from api.models.google import GoogleAccountConnection
import api.services.google_oauth as google_oauth


def _access_token(
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


def test_google_authorization_is_send_only_and_bound_to_local_account(
    api_client,
    monkeypatch,
) -> None:
    client, _ = api_client
    monkeypatch.setenv(
        'GOOGLE_OAUTH_CLIENT_ID',
        'test-desktop-client.apps.googleusercontent.com',
    )
    user_token: str = _access_token(
        client,
        'user@example.com',
        'user-password',
    )
    admin_token: str = _access_token(
        client,
        'admin@example.com',
        'admin-password',
    )
    response = client.post(
        '/integrations/google/authorize',
        headers={
            'Authorization': f'Bearer {user_token}',
            'Host': '127.0.0.1:8765',
        },
    )

    assert response.status_code == 200, response.text
    flow_id: str = response.json()['flow_id']
    authorization_url: str = response.json()['authorization_url']
    query = parse_qs(urlparse(authorization_url).query)
    scopes: set[str] = set(query['scope'][0].split())
    assert scopes == {
        'openid',
        'email',
        'https://www.googleapis.com/auth/gmail.send',
    }
    assert 'code_challenge' in query
    assert query['code_challenge_method'] == ['S256']
    assert query['access_type'] == ['offline']
    assert 'client_secret' not in query
    owner_status = client.get(
        f'/integrations/google/callback/{flow_id}',
        headers={'Authorization': f'Bearer {user_token}'},
    )
    other_user_status = client.get(
        f'/integrations/google/callback/{flow_id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert owner_status.status_code == 200
    assert owner_status.json()['status'] == 'pending'
    assert other_user_status.status_code == 400


def test_google_email_sender_and_recipient_are_the_connected_account() -> None:
    from api.services.google_mail import (
        GoogleEmailAttachment,
        build_google_email,
    )

    message = build_google_email(
        'owner@example.com',
        'Finance Scraper report',
        'Your report is attached.',
        [
            GoogleEmailAttachment(
                filename='AAPL.pdf',
                content_type='application/pdf',
                content=b'%PDF-data',
            ),
        ],
    )

    assert message['From'] == 'Finance Scraper <owner@example.com>'
    assert message['To'] == 'owner@example.com'
    assert len(message.get_payload()) == 2


def test_google_oauth_callback_uses_pkce_and_stores_opaque_refresh_token(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        'GOOGLE_OAUTH_CLIENT_ID',
        'test-desktop-client.apps.googleusercontent.com',
    )
    account_id: str = 'account-test'
    callback_url: str = (
        'http://127.0.0.1:8765/integrations/google/callback'
    )
    flow_id, authorization_url = google_oauth.start_google_oauth(
        account_id,
        callback_url,
    )
    query = parse_qs(urlparse(authorization_url).query)
    original_async_client = httpx.AsyncClient
    token_form: dict[str, list[str]] = {}

    async def mock_google(request: httpx.Request) -> httpx.Response:
        if request.url.path == '/token':
            token_form.update(parse_form(request.content.decode('utf-8')))
            return httpx.Response(
                200,
                json={
                    'access_token': 'short-lived-access-token',
                    'refresh_token': 'opaque-refresh-token',
                    'scope': (
                        'openid email '
                        'https://www.googleapis.com/auth/gmail.send'
                    ),
                },
            )
        return httpx.Response(
            200,
            json={
                'email': 'owner@example.com',
                'email_verified': True,
            },
        )

    transport: httpx.MockTransport = httpx.MockTransport(mock_google)
    monkeypatch.setattr(
        google_oauth.httpx,
        'AsyncClient',
        lambda **kwargs: original_async_client(
            transport=transport,
            **kwargs,
        ),
    )
    stored_tokens: list[tuple[str, str]] = []

    def store_token(owner_id: str, token: str) -> None:
        stored_tokens.append((owner_id, token))

    async def save_connection(
        owner_id: str,
        email: str,
        scopes: tuple[str, ...],
    ) -> GoogleAccountConnection:
        return GoogleAccountConnection(
            account_id=owner_id,
            google_email=email,
            scopes=scopes,
            connected_at=1,
            updated_at=1,
        )

    monkeypatch.setattr(
        google_oauth,
        'store_google_refresh_token',
        store_token,
    )
    monkeypatch.setattr(
        google_oauth.GoogleRepository,
        'save_google_connection',
        save_connection,
    )

    email: str = asyncio.run(
        google_oauth.complete_google_oauth('authorization-code', flow_id),
    )
    flow = google_oauth.get_google_oauth_flow(account_id, flow_id)

    assert email == 'owner@example.com'
    assert stored_tokens == [(account_id, 'opaque-refresh-token')]
    assert token_form['code_verifier']
    assert token_form['redirect_uri'] == [callback_url]
    assert 'client_secret' not in token_form
    assert flow is not None
    assert flow.status == 'completed'
    assert flow.google_email == email
    assert query['code_challenge_method'] == ['S256']


def test_google_signin_creates_a_verified_single_use_identity_flow(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        'GOOGLE_OAUTH_CLIENT_ID',
        'test-desktop-client.apps.googleusercontent.com',
    )
    callback_url = 'http://127.0.0.1:8765/integrations/google/callback'
    flow_id, authorization_url = google_oauth.start_google_login(callback_url)
    query = parse_qs(urlparse(authorization_url).query)
    assert set(query['scope'][0].split()) == {'openid', 'email', 'profile'}
    assert query['prompt'] == ['select_account']

    original_async_client = httpx.AsyncClient
    token_form: dict[str, list[str]] = {}

    async def mock_google(request: httpx.Request) -> httpx.Response:
        if request.url.path == '/token':
            token_form.update(parse_form(request.content.decode('utf-8')))
            return httpx.Response(
                200,
                json={
                    'access_token': 'short-lived-login-token',
                    'scope': 'openid email profile',
                },
            )
        return httpx.Response(
            200,
            json={
                'sub': 'google-subject-123',
                'email': 'owner@example.com',
                'email_verified': True,
                'name': 'Google User',
            },
        )

    transport: httpx.MockTransport = httpx.MockTransport(mock_google)
    monkeypatch.setattr(
        google_oauth.httpx,
        'AsyncClient',
        lambda **kwargs: original_async_client(
            transport=transport,
            **kwargs,
        ),
    )

    asyncio.run(
        google_oauth.complete_google_oauth('authorization-code', flow_id),
    )
    flow = google_oauth.get_google_login_flow(flow_id)
    identity = google_oauth.consume_google_login_flow(flow_id)

    assert token_form['code_verifier']
    assert token_form['redirect_uri'] == [callback_url]
    assert 'client_secret' not in token_form
    assert flow is not None
    assert flow.status == 'completed'
    assert flow.google_email == 'owner@example.com'
    assert identity is not None
    assert identity.email == 'owner@example.com'
    assert identity.name == 'Google User'
    assert google_oauth.consume_google_login_flow(flow_id) is None
