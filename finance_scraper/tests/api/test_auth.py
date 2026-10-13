 
import pytest
from fastapi.testclient import TestClient

from api.routers import auth as auth_router
from api.services.google_oauth import GoogleLoginIdentity


def _login(
    client: TestClient,
    email: str = 'admin@example.com',
    password: str = 'admin-password',
):
    return client.post(
        '/auth/login',
        json={'email': email, 'password': password},
    )


def test_registration_requires_desktop_token_and_creates_user(
    api_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, state = api_client
    monkeypatch.setenv('FINANCE_DESKTOP_CONTROL_TOKEN', 'desktop-test-token')
    payload: dict[str, str] = {
        'name': 'New Local User',
        'email': 'new-local@example.com',
        'password': 'secure-password',
    }

    unauthorized_response = client.post('/auth/register', json=payload)
    registration_response = client.post(
        '/auth/register',
        headers={'X-Finance-Desktop-Token': 'desktop-test-token'},
        json=payload,
    )
    login_response = _login(
        client,
        'new-local@example.com',
        'secure-password',
    )

    assert unauthorized_response.status_code == 403
    assert registration_response.status_code == 201
    assert registration_response.json()['role'] == 'user'
    assert registration_response.json()['watchlist'] == []
    assert login_response.status_code == 200
    assert len(state['accounts']) == 3


def test_google_signin_creates_a_local_profile_for_a_new_verified_email(
    api_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, state = api_client
    monkeypatch.setenv('FINANCE_DESKTOP_CONTROL_TOKEN', 'desktop-test-token')
    identity = GoogleLoginIdentity(
        email='google-user@example.com',
        name='Google User',
    )

    async def get_account_by_email(email: str):
        return next(
            (
                account
                for account in state['accounts'].values()
                if str(account.email).casefold() == email.casefold()
            ),
            None,
        )

    monkeypatch.setattr(
        auth_router,
        'consume_google_login_flow',
        lambda flow_id: identity,
    )
    monkeypatch.setattr(
        auth_router.AccountRepository,
        'get_account_by_email',
        get_account_by_email,
    )

    response = client.post(
        '/auth/google/login',
        headers={'X-Finance-Desktop-Token': 'desktop-test-token'},
        json={'flow_id': 'verified-google-flow-id-1234567890'},
    )

    assert response.status_code == 200
    assert response.json()['access_token']
    account = next(
        item
        for item in state['accounts'].values()
        if item.email == identity.email
    )
    assert account.name == identity.name
    assert state['passwords'][identity.email]


def test_google_signin_uses_an_existing_account_with_the_verified_email(
    api_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, state = api_client
    monkeypatch.setenv('FINANCE_DESKTOP_CONTROL_TOKEN', 'desktop-test-token')
    identity = GoogleLoginIdentity(
        email='user@example.com',
        name='Updated Google Name',
    )
    existing_account = next(
        item
        for item in state['accounts'].values()
        if item.email == identity.email
    )

    async def get_account_by_email(email: str):
        return existing_account if email.casefold() == identity.email else None

    async def create_account(payload):
        raise AssertionError('Google sign-in must reuse the matching account')

    monkeypatch.setattr(
        auth_router,
        'consume_google_login_flow',
        lambda flow_id: identity,
    )
    monkeypatch.setattr(
        auth_router.AccountRepository,
        'get_account_by_email',
        get_account_by_email,
    )
    monkeypatch.setattr(
        auth_router.AccountRepository,
        'create_account',
        create_account,
    )

    response = client.post(
        '/auth/google/login',
        headers={'X-Finance-Desktop-Token': 'desktop-test-token'},
        json={'flow_id': 'existing-google-flow-id-123456789'},
    )

    assert response.status_code == 200
    assert response.json()['access_token']


def test_login_refresh_replay_revokes_token_family(api_client) -> None:
    client, _ = api_client

    login_response = _login(client)

    assert login_response.status_code == 200
    first_pair = login_response.json()
    assert first_pair['access_token']
    assert first_pair['refresh_token']
    assert first_pair['expires_in'] > 0
    assert first_pair['refresh_expires_in'] > first_pair['expires_in']

    refresh_response = client.post(
        '/auth/refresh',
        json={'refresh_token': first_pair['refresh_token']},
    )

    assert refresh_response.status_code == 200
    second_pair = refresh_response.json()
    assert second_pair['refresh_token'] != first_pair['refresh_token']

    replay_response = client.post(
        '/auth/refresh',
        json={'refresh_token': first_pair['refresh_token']},
    )
    profile_response = client.get(
        '/accounts/me',
        headers={
            'Authorization': f'Bearer {second_pair["access_token"]}',
        },
    )

    assert replay_response.status_code == 401
    assert profile_response.status_code == 401
    assert replay_response.json()['error'] == 'INVALID_EXPIRED_TOKEN'


def test_logout_revokes_access_and_refresh_tokens(api_client) -> None:
    client, _ = api_client
    pair = _login(client).json()
    headers = {'Authorization': f'Bearer {pair["access_token"]}'}

    logout_response = client.post('/auth/logout', headers=headers)
    profile_response = client.get('/accounts/me', headers=headers)
    refresh_response = client.post(
        '/auth/refresh',
        json={'refresh_token': pair['refresh_token']},
    )

    assert logout_response.status_code == 200
    assert profile_response.status_code == 401
    assert refresh_response.status_code == 401


def test_request_validation_uses_common_error_response(api_client) -> None:
    client, _ = api_client

    response = client.post(
        '/auth/login',
        json={'email': 'not-an-email', 'password': ''},
    )

    assert response.status_code == 422
    assert response.json()['success'] is False
    assert response.json()['error'] == 'INVALID_REQUEST'
    assert response.json()['status_code'] == 422
    assert 'email' in response.json()['message']


def test_login_rate_limit_returns_common_error_response(api_client) -> None:
    client, _ = api_client
    for _ in range(5):
        response = _login(client, password='incorrect-password')
        assert response.status_code == 401

    limited_response = _login(client, password='incorrect-password')

    assert limited_response.status_code == 429
    assert limited_response.json() == {
        'success': False,
        'error': 'RATE_LIMIT_EXCEEDED',
        'message': 'Too many requests; try again later',
        'status_code': 429,
    }
    assert 'Retry-After' in limited_response.headers
