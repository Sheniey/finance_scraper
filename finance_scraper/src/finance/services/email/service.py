"""Send report emails through each account's authorized Google account."""

from collections.abc import Iterable
from datetime import date

from finance.services.email.exceptions import EmailDeliveryError
from finance.services.email.models import EmailAttachment


def build_report_notice(
    run_date: date,
    tickers: Iterable[str],
    *,
    account_name: str,
    language_code: str = 'es',
) -> tuple[str, str]:
    """Build a report message without identifying the application as sender."""

    normalized_tickers: list[str] = [
        ticker.strip().upper()
        for ticker in tickers
        if isinstance(ticker, str) and ticker.strip()
    ]
    if not normalized_tickers:
        raise ValueError('At least one ticker is required for a report email')

    normalized_name: str = account_name.strip()
    if not normalized_name or '\r' in normalized_name or '\n' in normalized_name:
        raise ValueError('The account name is invalid for an email header')

    ticker_label: str = ', '.join(normalized_tickers)
    if language_code.casefold().startswith('en'):
        subject: str = f'Financial report — {ticker_label} — {run_date.isoformat()}'
        body: str = (
            f'Hello {normalized_name},\n\n'
            f'Your report for {ticker_label} on {run_date.isoformat()} '
            'is attached. It was sent from your connected Google account.'
        )
    else:
        subject = f'Reporte financiero — {ticker_label} — {run_date.isoformat()}'
        body = (
            f'Hola {normalized_name},\n\n'
            f'Tu reporte de {ticker_label} del {run_date.isoformat()} '
            'está adjunto. Se envió desde tu cuenta de Google conectada.'
        )
    return subject, body


class EmailService:
    """Deliver account reports using the account's Google OAuth connection."""

    async def send_email(
        self,
        account_id: str,
        account_name: str,
        subject: str,
        text_body: str,
        attachments: Iterable[EmailAttachment] = (),
    ) -> str:
        from api.exceptions.google import (
            CredentialStoreUnavailableError,
            GoogleAccountNotConnectedError,
            GoogleOAuthNotConfiguredError,
            GoogleOAuthProviderError,
        )
        from api.services.google_mail import (
            GoogleEmailAttachment,
            send_google_email,
        )

        attachment_list: list[EmailAttachment] = list(attachments)
        if not all(
            isinstance(attachment, EmailAttachment)
            for attachment in attachment_list
        ):
            raise TypeError('Email attachments must be EmailAttachment instances')

        google_attachments: list[GoogleEmailAttachment] = [
            GoogleEmailAttachment(
                filename=attachment.filename,
                content_type=f'{attachment.maintype}/{attachment.subtype}',
                content=attachment.content,
            )
            for attachment in attachment_list
        ]
        try:
            return await send_google_email(
                account_id,
                subject,
                text_body,
                google_attachments,
                sender_name=account_name,
            )
        except (
            CredentialStoreUnavailableError,
            GoogleAccountNotConnectedError,
            GoogleOAuthNotConfiguredError,
            GoogleOAuthProviderError,
        ) as error:
            raise EmailDeliveryError(
                'The report could not be sent using the connected Google account.',
            ) from error

    async def send_report_bundle(
        self,
        account_id: str,
        account_name: str,
        run_date: date,
        tickers: Iterable[str],
        attachments: Iterable[EmailAttachment],
        *,
        language_code: str = 'es',
    ) -> str:
        """Send one account's report bundle through its authorized Gmail."""

        subject, body = build_report_notice(
            run_date,
            tickers,
            account_name=account_name,
            language_code=language_code,
        )
        return await self.send_email(
            account_id,
            account_name,
            subject,
            body,
            attachments,
        )


async def send_email(
    account_id: str,
    account_name: str,
    subject: str,
    text_body: str,
    attachments: Iterable[EmailAttachment] = (),
    *,
    service: EmailService | None = None,
) -> str:
    """Send one message through the authenticated account's Gmail."""

    return await (service or EmailService()).send_email(
        account_id,
        account_name,
        subject,
        text_body,
        attachments,
    )


async def send_report_bundle(
    account_id: str,
    account_name: str,
    run_date: date,
    tickers: Iterable[str],
    attachments: Iterable[EmailAttachment],
    *,
    language_code: str = 'es',
    service: EmailService | None = None,
) -> str:
    """Send one report bundle through its connected Google account."""

    return await (service or EmailService()).send_report_bundle(
        account_id,
        account_name,
        run_date,
        tickers,
        attachments,
        language_code=language_code,
    )
