 
from fastapi.testclient import TestClient


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


def test_admin_can_create_update_and_list_accounts(api_client) -> None:
    client, state = api_client
    admin_token: str = _access_token(
        client,
        'admin@example.com',
        'admin-password',
    )
    admin_headers: dict[str, str] = {
        'Authorization': f'Bearer {admin_token}',
    }

    create_response = client.post(
        '/accounts',
        headers=admin_headers,
        json={
            'name': 'New Account',
            'email': 'new@example.com',
            'password': 'new-password',
        },
    )

    assert create_response.status_code == 201, create_response.text
    account_id: str = create_response.json()['id']
    assert 'password' not in create_response.json()

    list_response = client.get(
        '/accounts',
        params={
            'page_size': 1,
            'fields': 'id,name,email',
            'sort': 'name',
        },
        headers=admin_headers,
    )
    filtered_response = client.get(
        '/accounts',
        params={'filter': '{"role":"user"}'},
        headers=admin_headers,
    )
    get_response = client.get(
        f'/accounts/{account_id}',
        headers=admin_headers,
    )
    update_response = client.put(
        f'/accounts/{account_id}',
        headers=admin_headers,
        json={
            'name': 'Renamed Account',
            'email': 'renamed@example.com',
        },
    )

    assert list_response.status_code == 200
    assert list_response.json()['pagination']['has_more'] is True
    assert set(list_response.json()['items'][0]) == {'id', 'name', 'email'}
    next_cursor: str = list_response.json()['pagination']['next_cursor']
    next_page_response = client.get(
        '/accounts',
        params={'page_cursor': next_cursor, 'page_size': 1, 'sort': 'name'},
        headers=admin_headers,
    )
    invalid_sort_response = client.get(
        '/accounts',
        params={'sort': 'password_hash'},
        headers=admin_headers,
    )
    assert filtered_response.json()['pagination']['total'] == 2
    assert next_page_response.status_code == 200
    assert (
        next_page_response.json()['items'][0]['id']
        != list_response.json()['items'][0]['id']
    )
    assert invalid_sort_response.status_code == 422
    assert invalid_sort_response.json()['error'] == 'INVALID_COLLECTION_QUERY'
    assert get_response.status_code == 200
    assert update_response.status_code == 200
    assert update_response.json()['name'] == 'Renamed Account'
    assert 'new@example.com' not in state['passwords']
    assert state['passwords']['renamed@example.com'] == 'new-password'


def test_non_admin_can_only_access_own_account(api_client) -> None:
    client, state = api_client
    user = next(
        account
        for account in state['accounts'].values()
        if str(account.email) == 'user@example.com'
    )
    user_token: str = _access_token(
        client,
        'user@example.com',
        'user-password',
    )
    headers: dict[str, str] = {'Authorization': f'Bearer {user_token}'}

    profile_response = client.get('/accounts/me', headers=headers)
    list_response = client.get('/accounts', headers=headers)
    other_account_response = client.get(
        f'/accounts/{state["admin"].id}',
        headers=headers,
    )

    assert profile_response.status_code == 200
    assert profile_response.json()['id'] == str(user.id)
    assert list_response.status_code == 403
    assert other_account_response.status_code == 403


def test_user_can_update_own_watchlist(api_client) -> None:
    client, state = api_client
    account = next(
        account
        for account in state['accounts'].values()
        if str(account.email) == 'user@example.com'
    )
    access_token: str = _access_token(
        client,
        'user@example.com',
        'user-password',
    )
    response = client.put(
        '/accounts/me',
        headers={'Authorization': f'Bearer {access_token}'},
        json={
            'name': account.name,
            'email': str(account.email),
            'watchlist': [
                {
                    'ticker': 'AAPL',
                    'region': 'US',
                    'mode': 'custom',
                    'llm_explanation': False,
                    'charts': True,
                    'horizon': 15,
                    'enabled': True,
                },
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()['role'] == 'user'
    assert response.json()['watchlist'][0]['ticker'] == 'AAPL'


def test_change_password_revokes_existing_sessions(api_client) -> None:
    client, _ = api_client
    access_token: str = _access_token(
        client,
        'user@example.com',
        'user-password',
    )
    headers: dict[str, str] = {'Authorization': f'Bearer {access_token}'}

    change_response = client.post(
        '/accounts/me/change-password',
        headers=headers,
        json={
            'current_password': 'user-password',
            'new_password': 'updated-password',
        },
    )
    old_session_response = client.get('/accounts/me', headers=headers)
    old_password_response = client.post(
        '/auth/login',
        json={
            'email': 'user@example.com',
            'password': 'user-password',
        },
    )
    new_password_response = client.post(
        '/auth/login',
        json={
            'email': 'user@example.com',
            'password': 'updated-password',
        },
    )

    assert change_response.status_code == 200
    assert old_session_response.status_code == 401
    assert old_password_response.status_code == 401
    assert new_password_response.status_code == 200


def test_delete_me_deletes_account_and_revokes_sessions(api_client) -> None:
    client, state = api_client
    access_token: str = _access_token(
        client,
        'user@example.com',
        'user-password',
    )
    headers: dict[str, str] = {'Authorization': f'Bearer {access_token}'}
    user_id: str = next(
        identifier
        for identifier, account in state['accounts'].items()
        if str(account.email) == 'user@example.com'
    )

    delete_response = client.delete('/accounts/me', headers=headers)
    profile_response = client.get('/accounts/me', headers=headers)
    login_response = client.post(
        '/auth/login',
        json={
            'email': 'user@example.com',
            'password': 'user-password',
        },
    )

    assert delete_response.status_code == 200
    assert user_id not in state['accounts']
    assert profile_response.status_code == 401
    assert login_response.status_code == 401
