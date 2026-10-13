import asyncio
import base64
import json
from email import message_from_bytes
from urllib.parse import parse_qs

import httpx

from api.models.google import GoogleAccountConnection
import api.services.google_mail as google_mail


def test_google_mail_refreshes_and_sends_only_from_connected_account(
    monkeypatch,
) -> None:
    account_id: str = 'local-account-one'
    connection: GoogleAccountConnection = GoogleAccountConnection(
        account_id=account_id,
        google_email='owner@example.com',
        scopes=('openid', 'email', 'https://www.googleapis.com/auth/gmail.send'),
        connected_at=1,
        updated_at=1,
    )
    monkeypatch.setenv(
        'GOOGLE_OAUTH_CLIENT_ID',
        'test-desktop-client.apps.googleusercontent.com',
    )

    async def get_connection(requested_account_id: str):
        assert requested_account_id == account_id
        return connection

    def get_refresh_token(requested_account_id: str):
        assert requested_account_id == account_id
        return 'opaque-refresh-token'

    original_async_client = httpx.AsyncClient
    requests: list[httpx.Request] = []

    async def google_endpoint(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == '/token':
            form = parse_qs(request.content.decode('utf-8'))
            assert form['grant_type'] == ['refresh_token']
            assert form['refresh_token'] == ['opaque-refresh-token']
            assert 'client_secret' not in form
            return httpx.Response(
                200,
                json={'access_token': 'short-lived-access-token'},
            )
        return httpx.Response(200, json={'id': 'sent-message'})

    transport = httpx.MockTransport(google_endpoint)
    monkeypatch.setattr(
        google_mail.httpx,
        'AsyncClient',
        lambda **kwargs: original_async_client(
            transport=transport,
            **kwargs,
        ),
    )
    monkeypatch.setattr(
        google_mail.GoogleRepository,
        'get_google_connection',
        get_connection,
    )
    monkeypatch.setattr(
        google_mail,
        'get_google_refresh_token',
        get_refresh_token,
    )

    asyncio.run(
        google_mail.send_google_email(
            account_id,
            'Finance Scraper report',
            'Your AAPL report is attached.',
            [
                google_mail.GoogleEmailAttachment(
                    filename='AAPL.pdf',
                    content_type='application/pdf',
                    content=b'%PDF report',
                ),
            ],
        ),
    )

    assert len(requests) == 2
    assert requests[1].headers['authorization'] == (
        'Bearer short-lived-access-token'
    )
    gmail_payload: dict[str, str] = json.loads(requests[1].content)
    raw_message = gmail_payload['raw']
    decoded = base64.urlsafe_b64decode(
        raw_message + '=' * (-len(raw_message) % 4),
    )
    message = message_from_bytes(decoded)
    assert message['From'] == 'Finance Scraper <owner@example.com>'
    assert message['To'] == 'owner@example.com'
    attachment = message.get_payload()[1]
    assert attachment.get_filename() == 'AAPL.pdf'
    assert attachment.get_payload(decode=True) == b'%PDF report'
