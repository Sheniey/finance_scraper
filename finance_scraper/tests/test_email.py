import asyncio
from datetime import date
from types import SimpleNamespace
from uuid import UUID

import pytest

from finance.renderers import RendererFactory
from finance.renderers.exceptions import RendererNotFoundError
from finance.services.account import Account, WatchlistItem
from finance.services.email import (
    EmailAttachment,
    EmailService,
    build_report_notice,
)
from finance.services.watchlist_dispatcher import WatchlistDispatcher


def test_report_notice_uses_account_identity_not_application_name() -> None:
    subject, body = build_report_notice(
        date(2026, 8, 29),
        ['AAPL', 'MSFT'],
        account_name='Alex Rivera',
        language_code='en',
    )

    assert subject == 'Financial report — AAPL, MSFT — 2026-08-29'
    assert 'Hello Alex Rivera' in body
    assert 'Finance Scraper' not in subject + body


def test_email_service_sends_through_the_accounts_connected_google_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import api.services.google_mail as google_mail

    sent_messages: list[tuple[object, ...]] = []

    async def send_google_email(
        account_id: str,
        subject: str,
        text_body: str,
        attachments,
        *,
        sender_name: str,
    ) -> str:
        sent_messages.append(
            (account_id, subject, text_body, list(attachments), sender_name),
        )
        return 'owner@gmail.com'

    monkeypatch.setattr(
        google_mail,
        'send_google_email',
        send_google_email,
    )
    attachment = EmailAttachment(
        'report_aapl.pdf',
        b'%PDF-1.7',
        maintype='application',
        subtype='pdf',
    )
    sender_email = asyncio.run(
        EmailService().send_report_bundle(
            'account-123',
            'Alex Rivera',
            date(2026, 8, 29),
            ['AAPL'],
            [attachment],
            language_code='es',
        ),
    )

    assert sender_email == 'owner@gmail.com'
    assert sent_messages[0][0] == 'account-123'
    assert sent_messages[0][4] == 'Alex Rivera'
    assert 'Hola Alex Rivera' in sent_messages[0][2]
    assert sent_messages[0][3][0].filename == 'report_aapl.pdf'
    assert sent_messages[0][3][0].content_type == 'application/pdf'


def test_report_notice_rejects_empty_ticker_list() -> None:
    with pytest.raises(ValueError, match='At least one ticker'):
        build_report_notice(
            date(2026, 8, 29),
            [],
            account_name='Alex Rivera',
        )


def test_dispatcher_sends_one_bundle_from_each_profile_google_account() -> None:
    calls: list[tuple[object, ...]] = []

    async def generate_report(*args, **kwargs):
        return SimpleNamespace()

    def render_attachment(report, *, filename):
        return EmailAttachment(filename, b'%PDF-1.7')

    class FakeEmailService:
        async def send_report_bundle(self, *args, **kwargs) -> str:
            calls.append((*args, kwargs))
            return 'account@gmail.com'

    account = Account(
        name='Profile Owner',
        email='account@example.com',
        account_id=UUID('00000000-0000-0000-0000-000000000123'),
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
        ),
    )

    assert result.email_sent
    assert result.generated_tickers == ('AAPL', 'MSFT')
    assert len(calls) == 1
    assert calls[0][0] == '00000000-0000-0000-0000-000000000123'
    assert calls[0][1] == 'Profile Owner'
    assert calls[0][2] == date(2026, 8, 29)
    assert calls[0][3] == ('AAPL', 'MSFT')
    assert calls[0][5]['language_code'] == 'en'
    assert [item.filename for item in calls[0][4]] == [
        'report_aapl--2026-08-29.pdf',
        'report_msft--2026-08-29.pdf',
    ]


def test_dispatcher_continues_after_one_ticker_fails() -> None:
    sent_bundles: list[tuple[object, ...]] = []

    async def generate_report(account, ticker, **kwargs):
        if ticker.ticker == 'BAD':
            raise ValueError('ticker failed')
        return SimpleNamespace()

    def render_attachment(report, *, filename):
        return EmailAttachment(filename, b'%PDF-1.7')

    class FakeEmailService:
        async def send_report_bundle(self, *args, **kwargs) -> str:
            sent_bundles.append(args)
            return 'account@gmail.com'

    account = Account(
        name='Profile Owner',
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
    assert sent_bundles[0][3] == ('GOOD',)


def test_renderer_factory_no_longer_registers_email() -> None:
    with pytest.raises(RendererNotFoundError):
        RendererFactory.create('email')
