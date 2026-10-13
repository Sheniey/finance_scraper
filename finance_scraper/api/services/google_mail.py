import asyncio
import base64
import os
from collections.abc import Sequence
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr

import httpx

from api.exceptions.google import (
    GoogleAccountNotConnectedError,
    GoogleOAuthNotConfiguredError,
    GoogleOAuthProviderError,
)
from api.repositories import google as GoogleRepository
from api.services.credential_store import (
    delete_google_refresh_token,
    get_google_refresh_token,
)


_TOKEN_ENDPOINT: str = 'https://oauth2.googleapis.com/token'
_SEND_ENDPOINT: str = (
    'https://gmail.googleapis.com/gmail/v1/users/me/messages/send'
)


@dataclass(frozen=True, slots=True)
class GoogleEmailAttachment:
    filename: str
    content_type: str
    content: bytes


def build_google_email(
    recipient: str,
    subject: str,
    text_body: str,
    attachments: Sequence[GoogleEmailAttachment],
) -> EmailMessage:
    if not subject.strip() or '\r' in subject or '\n' in subject:
        raise ValueError('Email subject must not be blank or contain line breaks')
    if not text_body.strip():
        raise ValueError('Email body must not be blank')

    message: EmailMessage = EmailMessage()
    message['From'] = formataddr(('Finance Scraper', recipient))
    message['To'] = recipient
    message['Subject'] = subject
    message.set_content(text_body)
    for attachment in attachments:
        maintype, _, subtype = attachment.content_type.partition('/')
        if not maintype or not subtype:
            maintype, subtype = 'application', 'octet-stream'
        message.add_attachment(
            attachment.content,
            maintype=maintype,
            subtype=subtype,
            filename=attachment.filename,
        )
    return message


async def _refresh_access_token(
    account_id: str,
    refresh_token: str,
) -> str:
    client_id: str = (os.getenv('GOOGLE_OAUTH_CLIENT_ID') or '').strip()
    if not client_id:
        raise GoogleOAuthNotConfiguredError()

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                _TOKEN_ENDPOINT,
                data={
                    'client_id': client_id,
                    'grant_type': 'refresh_token',
                    'refresh_token': refresh_token,
                },
            )
    except httpx.HTTPError as e:
        raise GoogleOAuthProviderError(
            'Google could not renew the Gmail authorization',
        ) from e

    if response.is_error:
        try:
            response_data: object = response.json()
        except ValueError as e:
            raise GoogleOAuthProviderError(
                'Google could not renew the Gmail authorization',
            ) from e
        if (
            isinstance(response_data, dict)
            and response_data.get('error') == 'invalid_grant'
        ):
            await asyncio.to_thread(
                delete_google_refresh_token,
                account_id,
            )
            await GoogleRepository.delete_google_connection(account_id)
            raise GoogleAccountNotConnectedError()
        raise GoogleOAuthProviderError(
            'Google could not renew the Gmail authorization',
        )

    try:
        token_data: object = response.json()
    except ValueError as e:
        raise GoogleOAuthProviderError(
            'Google returned an invalid token response',
        ) from e
    access_token: object = (
        token_data.get('access_token')
        if isinstance(token_data, dict)
        else None
    )
    if not isinstance(access_token, str) or not access_token:
        raise GoogleOAuthProviderError(
            'Google returned an invalid token response',
        )
    return access_token


async def send_google_email(
    account_id: str,
    subject: str,
    text_body: str,
    attachments: Sequence[GoogleEmailAttachment] = (),
) -> None:
    connection = await GoogleRepository.get_google_connection(account_id)
    if connection is None:
        raise GoogleAccountNotConnectedError()

    refresh_token: str | None = await asyncio.to_thread(
        get_google_refresh_token,
        account_id,
    )
    if refresh_token is None:
        raise GoogleAccountNotConnectedError()

    access_token: str = await _refresh_access_token(
        account_id,
        refresh_token,
    )
    message: EmailMessage = build_google_email(
        connection.google_email,
        subject,
        text_body,
        attachments,
    )
    raw_message: str = base64.urlsafe_b64encode(
        message.as_bytes(),
    ).decode('ascii').rstrip('=')
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                _SEND_ENDPOINT,
                headers={'Authorization': f'Bearer {access_token}'},
                json={'raw': raw_message},
            )
            response.raise_for_status()
    except httpx.HTTPError as e:
        raise GoogleOAuthProviderError(
            'Gmail could not send the Finance Scraper report',
        ) from e
