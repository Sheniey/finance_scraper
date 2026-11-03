from fastapi.testclient import TestClient

from api.routers import portfolio as portfolio_router
from finance.services.account.models import Action, Stock


def _user_token(client: TestClient) -> str:
    response = client.post(
        '/auth/login',
        json={
            'email': 'user@example.com',
            'password': 'user-password',
        },
    )
    assert response.status_code == 200, response.text
    return response.json()['access_token']


def test_user_can_record_and_read_a_portfolio_trade(
    api_client,
    monkeypatch,
) -> None:
    client, state = api_client
    token = _user_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    account = next(
        account
        for account in state['accounts'].values()
        if str(account.email) == 'user@example.com'
    )

    async def add_portfolio_trade(current_account, payload):
        holding = Stock(
            ticker=payload.ticker,
            region=payload.region,
            currency=payload.currency,
            actions=[
                Action(
                    action=payload.action,
                    price=payload.price,
                    quantity=payload.quantity,
                    date=payload.date.isoformat(),
                ),
            ],
        )
        updated_account = current_account.model_copy(
            update={'portfolio': [holding]},
        )
        state['accounts'][str(current_account.id)] = updated_account
        return updated_account

    monkeypatch.setattr(
        portfolio_router.AccountRepository,
        'add_portfolio_trade',
        add_portfolio_trade,
    )

    empty_response = client.get('/portfolio/me', headers=headers)
    trade_response = client.post(
        '/portfolio/me/trades',
        headers=headers,
        json={
            'action': 'BUY',
            'ticker': 'aapl',
            'region': 'us',
            'currency': 'usd',
            'price': 184.5,
            'quantity': 3,
            'date': '2026-10-18',
        },
    )
    portfolio_response = client.get('/portfolio/me', headers=headers)

    assert empty_response.status_code == 200
    assert empty_response.json()['portfolio'] == []
    assert trade_response.status_code == 201
    assert trade_response.json()['portfolio'][0]['ticker'] == 'AAPL'
    assert portfolio_response.status_code == 200
    assert portfolio_response.json()['portfolio'][0]['actions'] == [
        {
            'action': 'BUY',
            'price': 184.5,
            'quantity': 3,
            'date': '2026-10-18',
        },
    ]
    assert account.id == state['accounts'][str(account.id)].id


def test_portfolio_trade_rejects_invalid_price_and_quantity(api_client) -> None:
    client, _ = api_client
    token = _user_token(client)

    response = client.post(
        '/portfolio/me/trades',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'action': 'BUY',
            'ticker': 'AAPL',
            'region': 'US',
            'currency': 'USD',
            'price': 0,
            'quantity': 0,
            'date': '2026-10-18',
        },
    )

    assert response.status_code == 422
    assert response.json()['error'] == 'INVALID_REQUEST'
