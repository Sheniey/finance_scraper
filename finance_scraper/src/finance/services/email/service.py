
import os, ssl, smtplib
from collections.abc import Callable, Iterable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date
from email.message import EmailMessage
from email.utils import parseaddr
from typing import Protocol

from finance.config import (
    EMAIL_ADDRESS, EMAIL_PORT,
    EMAIL_HOST, EMAIL_PASSWORD,
    EMAIL_TIMEOUT,
    EMAIL_USE_TLS, EMAIL_USE_SSL
)
from finance.services.email.exceptions import (
    EmailConfigurationError,
    InvalidConfigurationError,
)
from finance.services.email.models import EmailAttachment


class SMTPConnection(Protocol):
    """
    Subset of an SMTP client required by :class:`EmailService`.
    """

    def __enter__(self) -> 'SMTPConnection':
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> bool | None:
        ...

    def starttls(self, *, context: ssl.SSLContext) -> None:
        ...

    def login(self, user: str, password: str) -> None:
        ...

    def send_message(self, message: EmailMessage) -> None:
        ...


type SMTPFactory = Callable[..., AbstractContextManager[SMTPConnection]]


# ================================================== # 
# DATACLASSES                                        #
# ================================================== #

@dataclass(frozen=True)
class SMTPSettings:
    """
    SMTP connection settings used by :class:`EmailService`.
    """

    host: str
    port: int
    sender: str
    password: str | None
    use_tls: bool
    use_ssl: bool
    timeout: float


# ================================================== # 
# HELPER FUNCTIONS                                   #
# ================================================== #

def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default

    normalized: str = value.strip().lower()
    if normalized in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'off'}:
        return False
    
    raise InvalidConfigurationError(
        'email boolean setting', value, f'Invalid boolean value: {value!r}',
    )

def get_smtp_settings() -> SMTPSettings:
    """Load and validate SMTP settings from the environment."""

    host: str = (os.getenv('EMAIL_HOST') or EMAIL_HOST or '').strip()
    sender: str = (os.getenv('EMAIL_ADDRESS') or EMAIL_ADDRESS or '').strip()
    password: str | None = os.getenv('EMAIL_PASSWORD')
    if password is None:
        password = EMAIL_PASSWORD
    password = password.strip() if password else None

    if not host:
        raise EmailConfigurationError('EMAIL_HOST must be configured to send emails')
    if not sender:
        raise EmailConfigurationError('EMAIL_ADDRESS must be configured to send emails')
    if '\r' in sender or '\n' in sender:
        raise EmailConfigurationError('EMAIL_ADDRESS must not contain line breaks')

    raw_port: str | int = os.getenv('EMAIL_PORT') or EMAIL_PORT or 587
    try:
        port: int = int(raw_port)
    except (TypeError, ValueError) as e:
        raise InvalidConfigurationError(
            'EMAIL_PORT',
            raw_port,
            f'EMAIL_PORT must be an integer: {raw_port!r}',
        ) from e
    if not 1 <= port <= 65535:
        raise EmailConfigurationError('EMAIL_PORT must be between 1 and 65535')

    use_ssl: bool = _parse_bool(
        os.getenv('EMAIL_USE_SSL') or EMAIL_USE_SSL,
        port == 465,
    )
    use_tls: bool = _parse_bool(
        os.getenv('EMAIL_USE_TLS') or EMAIL_USE_TLS,
        not use_ssl,
    )
    if use_ssl and use_tls:
        raise EmailConfigurationError('EMAIL_USE_SSL and EMAIL_USE_TLS cannot both be enabled')

    raw_timeout: str = os.getenv('EMAIL_TIMEOUT') or EMAIL_TIMEOUT or '30'
    try:
        timeout: float = float(raw_timeout)
    except (TypeError, ValueError) as e:
        raise InvalidConfigurationError(
            'EMAIL_TIMEOUT',
            raw_timeout,
            f'EMAIL_TIMEOUT must be a number: {raw_timeout!r}',
        ) from e
    
    if timeout <= 0:
        raise EmailConfigurationError('EMAIL_TIMEOUT must be positive')

    return SMTPSettings(
        host=host,
        port=port,
        sender=sender,
        password=password,
        use_tls=use_tls,
        use_ssl=use_ssl,
        timeout=timeout,
    )


def _normalize_recipients(to: str | Iterable[str]) -> list[str]:
    if isinstance(to, str):
        values: list[str] = [to]
    else:
        values = list(to)

    if not values:
        raise ValueError('At least one email recipient is required')

    recipients: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise TypeError('Email recipients must be strings')
        recipient: str = value.strip()
        parsed_address: str = parseaddr(recipient)[1]

        if (
            not parsed_address
            or '\r' in recipient
            or '\n' in recipient
            or parsed_address.count('@') != 1
            or parsed_address.startswith('@')
            or parsed_address.endswith('@')
        ):
            raise ValueError(f'Invalid email recipient: {value!r}')
        recipients.append(recipient)
    return recipients


def build_report_notice(
    run_date: date,
    tickers: Iterable[str],
) -> tuple[str, str]:
    """Build the short subject and body used by every PDF delivery."""

    normalized_tickers: list[str] = [
        ticker.strip().upper()
        for ticker in tickers
        if isinstance(ticker, str) and ticker.strip()
    ]
    if not normalized_tickers:
        raise ValueError('At least one ticker is required for a report email')

    ticker_label: str = ', '.join(normalized_tickers)
    report_label: str = (
        'tu reporte'
        if len(normalized_tickers) == 1
        else 'tus reportes'
    )
    subject: str = f'Finance Scraper - {ticker_label} - {run_date.isoformat()}'
    body: str = (
        f'Aquí tienes {report_label} acerca de {ticker_label} '
        f'para el día {run_date.isoformat()}.'
    )
    return subject, body


class EmailService:
    """Send multipart messages through a configured SMTP server."""

    def __init__(
        self,
        settings: SMTPSettings | None = None,
        *,
        smtp_factory: SMTPFactory | None = None,
        smtp_ssl_factory: SMTPFactory | None = None,
    ) -> None:
        self.__settings: SMTPSettings | None = settings
        self.__smtp_factory: SMTPFactory = smtp_factory or smtplib.SMTP
        self.__smtp_ssl_factory: SMTPFactory = (
            smtp_ssl_factory or smtplib.SMTP_SSL
        )

    def send_email(
        self,
        to: str | Iterable[str],
        subject: str,
        text_body: str | None = None,
        *,
        body: str | None = None,
        html_body: str | None = None,
        attachments: Iterable[EmailAttachment] = (),
    ) -> None:
        """Send a plain-text or multipart email, optionally with attachments."""

        recipients: list[str] = _normalize_recipients(to)
        if not isinstance(subject, str) or not subject.strip():
            raise ValueError('Email subject must not be blank')
        if '\r' in subject or '\n' in subject:
            raise ValueError('Email subject must not contain line breaks')
        if text_body is None:
            text_body = body
        if text_body is None:
            raise ValueError('Email text body is required')
        if not isinstance(text_body, str):
            raise TypeError('Email text body must be a string')
        if html_body is not None and not isinstance(html_body, str):
            raise TypeError('Email HTML body must be a string')
        attachment_list: list[EmailAttachment] = list(attachments)
        if not all(
            isinstance(attachment, EmailAttachment)
            for attachment in attachment_list
        ):
            raise TypeError('Email attachments must be EmailAttachment instances')

        settings: SMTPSettings = self.__settings or get_smtp_settings()
        message: EmailMessage = EmailMessage()
        message['Subject'] = subject.strip()
        message['From'] = settings.sender
        message['To'] = ', '.join(recipients)
        message.set_content(text_body)
        if html_body is not None:
            message.add_alternative(html_body, subtype='html')
        for attachment in attachment_list:
            message.add_attachment(
                attachment.content,
                maintype=attachment.maintype,
                subtype=attachment.subtype,
                filename=attachment.filename,
            )

        if settings.use_ssl:
            with self.__smtp_ssl_factory(
                settings.host,
                settings.port,
                timeout=settings.timeout,
                context=ssl.create_default_context(),
            ) as server:
                self._authenticate(server, settings)
                server.send_message(message)
            return

        with self.__smtp_factory(
            settings.host,
            settings.port,
            timeout=settings.timeout,
        ) as server:
            if settings.use_tls:
                server.starttls(context=ssl.create_default_context())
            self._authenticate(server, settings)
            server.send_message(message)

    def send(
        self,
        to: str | Iterable[str],
        subject: str,
        text_body: str | None = None,
        *,
        body: str | None = None,
        html_body: str | None = None,
        attachments: Iterable[EmailAttachment] = (),
    ) -> None:
        """Alias for :meth:`send_email`."""

        self.send_email(
            to,
            subject,
            text_body,
            body=body,
            html_body=html_body,
            attachments=attachments,
        )

    def send_report_bundle(
        self,
        to: str | Iterable[str],
        run_date: date,
        tickers: Iterable[str],
        attachments: Iterable[EmailAttachment],
    ) -> None:
        """Send a short plain-text notice with PDF report attachments."""

        subject: str
        text_body: str
        subject, text_body = build_report_notice(run_date, tickers)
        attachment_list: list[EmailAttachment] = list(attachments)
        if not attachment_list:
            raise ValueError('At least one PDF attachment is required')
        if any(
            not attachment.filename.lower().endswith('.pdf')
            for attachment in attachment_list
        ):
            raise ValueError('Report emails only support PDF attachments')
        self.send_email(
            to,
            subject,
            text_body,
            attachments=attachment_list,
        )

    @staticmethod
    def _authenticate(server: SMTPConnection, settings: SMTPSettings) -> None:
        if settings.password:
            server.login(settings.sender, settings.password)


def send_email(
    to: str | Iterable[str],
    subject: str,
    text_body: str | None = None,
    *,
    body: str | None = None,
    html_body: str | None = None,
    service: EmailService | None = None,
    attachments: Iterable[EmailAttachment] = (),
) -> None:
    """Send one email using a new or injected :class:`EmailService`."""

    (service or EmailService()).send_email(
        to,
        subject,
        text_body,
        body=body,
        html_body=html_body,
        attachments=attachments,
    )


def send_report_bundle(
    to: str | Iterable[str],
    run_date: date,
    tickers: Iterable[str],
    attachments: Iterable[EmailAttachment],
    service: EmailService | None = None,
) -> None:
    """Send a PDF report bundle using a new or injected service."""

    (service or EmailService()).send_report_bundle(
        to,
        run_date,
        tickers,
        attachments,
    )
