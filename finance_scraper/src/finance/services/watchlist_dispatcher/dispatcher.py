"""Generate and deliver reports for every account watchlist."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date
from smtplib import SMTPException

from finance.services.account.db import load_accounts
from finance.services.account.models import Account, WatchlistItem
from finance.services.email import EmailAttachment, EmailException, EmailService
from finance.services.report_delivery import render_pdf_attachment
from finance.services.reporter.models import Report
from finance.services.reporter.repository import generate_report
from datatypes.ticker import Ticker


# ================================================== #
# TYPES                                              #
# ================================================== #

logger: logging.Logger = logging.getLogger(__name__)
type ReportGenerator = Callable[..., Awaitable[Report]]
type AttachmentRenderer = Callable[..., EmailAttachment]


@dataclass(frozen=True, slots=True)
class DispatchResult:
    """In-memory outcome for one account dispatch."""

    account_email: str
    generated_tickers: tuple[str, ...] = ()
    failed_tickers: tuple[str, ...] = ()
    email_sent: bool = False
    error: str | None = None

    @property
    def is_successful(self) -> bool:
        return bool(self.generated_tickers) and self.email_sent


# ================================================== #
# HELPERS                                            #
# ================================================== #

def _active_watchlist(account: Account) -> list[WatchlistItem]:
    return [
        item
        for item in account.watchlist
        if isinstance(item, WatchlistItem) and item.enabled
    ]


def _error_message(error: Exception) -> str:
    message: str = str(error).strip()
    return message or error.__class__.__name__


def _attachment_name(ticker: str, run_date: date) -> str:
    return f'report_{ticker.lower()}--{run_date.isoformat()}.pdf'


# ================================================== #
# DISPATCHER                                         #
# ================================================== #

class WatchlistDispatcher:
    """Dispatch every enabled watchlist item without persisting run state."""

    def __init__(
        self,
        *,
        report_generator: ReportGenerator | None = None,
        email_service: EmailService | None = None,
        attachment_renderer: AttachmentRenderer | None = None,
        max_concurrency: int = 3,
    ) -> None:
        if max_concurrency <= 0:
            raise ValueError('max_concurrency must be positive')

        self.__report_generator: ReportGenerator = (
            report_generator or generate_report
        )
        self.__email_service: EmailService = email_service or EmailService()
        self.__attachment_renderer: AttachmentRenderer = (
            attachment_renderer or render_pdf_attachment
        )
        self.__max_concurrency: int = max_concurrency

    async def dispatch_all_accounts(
        self,
        *,
        run_date: date | None = None,
    ) -> list[DispatchResult]:
        """Load every account off-thread and deliver each account's bundle."""

        accounts: list[Account] = await load_accounts()
        dispatch_date: date = run_date or date.today()
        semaphore: asyncio.Semaphore = asyncio.Semaphore(self.__max_concurrency)
        results: list[DispatchResult] = await asyncio.gather(
            *(
                self.__dispatch_account(account, dispatch_date, semaphore)
                for account in accounts
            )
        )
        return results

    async def dispatch_account(
        self,
        account: Account,
        *,
        run_date: date | None = None,
    ) -> DispatchResult:
        """Generate all enabled reports for one account and email their PDFs."""

        dispatch_date: date = run_date or date.today()
        semaphore: asyncio.Semaphore = asyncio.Semaphore(self.__max_concurrency)
        return await self.__dispatch_account(account, dispatch_date, semaphore)

    async def __dispatch_account(
        self,
        account: Account,
        dispatch_date: date,
        semaphore: asyncio.Semaphore,
    ) -> DispatchResult:
        active_items: list[WatchlistItem] = _active_watchlist(account)
        if not active_items:
            return DispatchResult(account_email=str(account.email))

        async def generate_attachment(
            item: WatchlistItem,
        ) -> tuple[str, EmailAttachment] | tuple[str, Exception]:
            async with semaphore:
                try:
                    report: Report = await self.__report_generator(
                        account,
                        Ticker(ticker=item.symbol),
                        generate_explanation=item.llm_explanation,
                        generate_charts=item.charts,
                        mode=item.mode,
                        horizon=item.horizon,
                        logging=False,
                    )
                    attachment: EmailAttachment = await asyncio.to_thread(
                        self.__attachment_renderer,
                        report,
                        filename=_attachment_name(item.symbol, dispatch_date),
                    )
                    return item.symbol, attachment
                except Exception as e:
                    logger.exception(
                        'Could not generate watchlist report for %s (%s)',
                        item.symbol,
                        account.email,
                    )
                    return item.symbol, error

        outcomes: list[tuple[str, EmailAttachment] | tuple[str, Exception]] = (
            await asyncio.gather(
                *(generate_attachment(item) for item in active_items)
            )
        )
        successful: list[tuple[str, EmailAttachment]] = [
            outcome
            for outcome in outcomes
            if isinstance(outcome[1], EmailAttachment)
        ]
        failed_tickers: tuple[str, ...] = tuple(
            ticker
            for ticker, outcome in outcomes
            if isinstance(outcome, Exception)
        )
        if not successful:
            return DispatchResult(
                account_email=str(account.email),
                failed_tickers=failed_tickers,
                error='No watchlist report could be generated',
            )

        tickers: tuple[str, ...] = tuple(ticker for ticker, _ in successful)
        attachments: tuple[EmailAttachment, ...] = tuple(
            attachment for _, attachment in successful
        )
        try:
            await asyncio.to_thread(
                self.__email_service.send_report_bundle,
                str(account.email),
                dispatch_date,
                tickers,
                attachments,
            )
        except (EmailException, OSError, SMTPException, ValueError) as e:
            logger.exception('Could not email reports to %s', account.email)
            return DispatchResult(
                account_email=str(account.email),
                generated_tickers=tickers,
                failed_tickers=failed_tickers,
                error=_error_message(error),
            )

        return DispatchResult(
            account_email=str(account.email),
            generated_tickers=tickers,
            failed_tickers=failed_tickers,
            email_sent=True,
        )


__all__: list[str] = [
    'AttachmentRenderer',
    'DispatchResult',
    'ReportGenerator',
    'WatchlistDispatcher',
]
