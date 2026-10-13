import asyncio
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from finance.renderers import RendererFactory
from finance.renderers.exceptions import RendererNotFoundError
from finance.services.account import Account, WatchlistItem
from finance.services.email import EmailAttachment, EmailService, SMTPSettings, build_report_notice
from finance.services.watchlist_dispatcher import WatchlistDispatcher


# ================================================== #
# SMTP TEST DOUBLE                                    #
# ================================================== #

class _FakeSMTP:
    instances: list['_FakeSMTP'] = []

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs
        self.started_tls = False
        self.credentials = None
        self.messages = []
        self.__class__.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None

    def starttls(self, **kwargs) -> None:
        self.started_tls = True

    def login(self, sender, password) -> None:
        self.credentials = (sender, password)

    def send_message(self, message) -> None:
        self.messages.append(message)


# ================================================== #
# EMAIL SERVICE                                      #
# ================================================== #

def test_send_report_bundle_creates_plain_text_multipart_email() -> None:
    service = EmailService(
        SMTPSettings(
            host='smtp.example.test',
            port=587,
            sender='sender@example.test',
            password='password',
            use_tls=True,
            use_ssl=False,
            timeout=5,
        ),
        smtp_factory=_FakeSMTP,
    )
    attachment = EmailAttachment('report_test.pdf', b'%PDF-1.7')

    service.send_report_bundle(
        'recipient@example.test',
        date(2026, 8, 29),
        ['TEST'],
        [attachment],
    )

    message = _FakeSMTP.instances[-1].messages[0]
    assert message['To'] == 'recipient@example.test'
    assert message['Subject'] == 'Finance Scraper - TEST - 2026-08-29'
    assert 'Aquí tienes tu reporte acerca de TEST para el día 2026-08-29.' in (
        message.get_body(preferencelist=('plain',)).get_content()
    )
    assert [
        part.get_filename()
        for part in message.iter_attachments()
    ] == ['report_test.pdf']


def test_build_report_notice_pluralizes_multiple_tickers() -> None:
    subject, body = build_report_notice(
        date(2026, 8, 29),
        ['AAPL', 'MSFT'],
    )

    assert subject == 'Finance Scraper - AAPL, MSFT - 2026-08-29'
    assert body == (
        'Aquí tienes tus reportes acerca de AAPL, MSFT para el día 2026-08-29.'
    )


def test_send_report_bundle_rejects_empty_recipient() -> None:
    service = EmailService(
        SMTPSettings(
            host='smtp.example.test',
            port=587,
            sender='sender@example.test',
            password='password',
            use_tls=True,
            use_ssl=False,
            timeout=5,
        ),
        smtp_factory=_FakeSMTP,
    )

    with pytest.raises(ValueError):
        service.send_report_bundle(
            '',
            date(2026, 8, 29),
            ['TEST'],
            [EmailAttachment('report_test.pdf', b'%PDF-1.7')],
        )


# ================================================== #
# DISPATCHER                                         #
# ================================================== #

def test_dispatcher_sends_one_bundle_per_account() -> None:
    calls: list[tuple[object, ...]] = []

    async def generate_report(*args, **kwargs):
        return SimpleNamespace()

    def render_attachment(report, *, filename):
        return EmailAttachment(filename, b'%PDF-1.7')

    class FakeEmailService:
        def send_report_bundle(self, *args) -> None:
            calls.append(args)

    account = Account(
        name='Test account',
        email='account@example.com',
        watchlist=[
            WatchlistItem(ticker='AAPL'),
            WatchlistItem(ticker='MSFT'),
        ],
    )
    dispatcher = WatchlistDispatcher(
        report_generator=generate_report,
        email_service=FakeEmailService(),
        attachment_renderer=render_attachment,
        max_concurrency=2,
    )

    result = asyncio.run(
        dispatcher.dispatch_account(
            account,
            run_date=date(2026, 8, 29),
        )
    )

    assert result.email_sent
    assert result.generated_tickers == ('AAPL', 'MSFT')
    assert len(calls) == 1
    assert calls[0][0] == 'account@example.com'
    assert calls[0][1] == date(2026, 8, 29)
    assert calls[0][2] == ('AAPL', 'MSFT')
    assert [item.filename for item in calls[0][3]] == [
        'report_aapl--2026-08-29.pdf',
        'report_msft--2026-08-29.pdf',
    ]


def test_dispatcher_continues_after_one_ticker_fails() -> None:
    calls: list[tuple[object, ...]] = []

    async def generate_report(account, ticker, **kwargs):
        if ticker.ticker == 'BAD':
            raise ValueError('ticker failed')
        return SimpleNamespace()

    def render_attachment(report, *, filename):
        return EmailAttachment(filename, b'%PDF-1.7')

    class FakeEmailService:
        def send_report_bundle(self, *args) -> None:
            calls.append(args)

    account = Account(
        name='Test account',
        email='account@example.com',
        watchlist=[
            WatchlistItem(ticker='BAD'),
            WatchlistItem(ticker='GOOD'),
        ],
    )
    dispatcher = WatchlistDispatcher(
        report_generator=generate_report,
        email_service=FakeEmailService(),
        attachment_renderer=render_attachment,
    )

    result = asyncio.run(dispatcher.dispatch_account(account))

    assert result.email_sent
    assert result.generated_tickers == ('GOOD',)
    assert result.failed_tickers == ('BAD',)
    assert calls[0][2] == ('GOOD',)


def test_renderer_factory_no_longer_registers_email() -> None:
    with pytest.raises(RendererNotFoundError):
        RendererFactory.create('email')


# ================================================== #
# CLI SEND                                          #
# ================================================== #

def test_send_report_cli_uses_pdf_bundle_delivery() -> None:
    import finance

    account = Account(name='Test account', email='account@example.com')
    report = SimpleNamespace(
        ticker=SimpleNamespace(ticker='TEST', symbol='TEST'),
    )
    attachment = EmailAttachment('report_test.pdf', b'%PDF-1.7')
    with (
        patch.object(
            finance,
            'get_account',
            new=AsyncMock(return_value=account),
        ),
        patch.object(finance, 'load_i18n'),
        patch.object(
            finance,
            'generate_report',
            new=AsyncMock(return_value=report),
        ),
        patch.object(finance, 'render_pdf_attachment', return_value=attachment),
        patch.object(finance, 'EmailService') as service_class,
    ):
        finance.SendReport(
            'TEST',
            email='account@example.com',
            password='test-password',
            verbose=False,
        )

    service_class.return_value.send_report_bundle.assert_called_once_with(
        'account@example.com',
        date.today(),
        ['TEST'],
        [attachment],
    )
