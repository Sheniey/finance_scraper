from fastapi.testclient import TestClient

from api.routers import reports as reports_router


def test_report_explanation_requires_a_configured_ai_provider(
    api_client,
    monkeypatch,
) -> None:
    client, _ = api_client
    login = client.post(
        '/auth/login',
        json={
            'email': 'user@example.com',
            'password': 'user-password',
        },
    )
    assert login.status_code == 200
    token: str = login.json()['access_token']
    monkeypatch.setattr(
        reports_router,
        'has_available_ai_provider',
        lambda: False,
    )

    response = client.post(
        '/reports/me',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'ticker': 'AAPL',
            'filename': 'AAPL.pdf',
            'explain': True,
            'mode': 'classic',
        },
    )

    assert response.status_code == 409
    assert response.json()['error'] == 'AI_PROVIDER_NOT_CONFIGURED'
