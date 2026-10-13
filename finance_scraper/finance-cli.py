
import asyncio
import mimetypes
from datetime import date
from pathlib import Path
from smtplib import SMTPException
from typing import Annotated
from typer import Typer, Argument, Option
from designkit.behavioral.verboser import VerboseSystem
from rich.table import Table

from datatypes import Ticker
from finance.config import console, IS_DEV
from finance.types import ReportMode
from finance.logging import (
    GENERATING_REPORT,
    EMAIL_SENT,
    EMAIL_DELIVERY_FAILED,
    NO_ACCOUNT_PROVIDED,
    NO_ACCOUNT_FOUND,
    ACCOUNT_ALREADY_EXISTS,
    RENDERER_NOT_SUPPORTED,
    TICKER_ADDED_TO_WATCHLIST,
    TICKER_NOT_FOUND,
    UNKNOWN_ERROR,
)
from finance.renderers.factory import RendererFactory
from finance.services.database import (
    sync_and_close_database_pools,
)
from finance.services.i18n import load_i18n
from finance.services.account import (
    Account, WatchlistItem,
    add_trade,
    add_watchlist_item,
    get_available_languages,
    get_available_language_styles,
    get_available_report_modes,
    get_by_email_or_name as get_account,
    get_by_name as get_account_by_name,
    remove_watchlist_item,
    create_account
)
from finance.services.account import Stock
from finance.services.account.exceptions import AccountAlreadyExistsError
from finance.services.yf_extractor import TickerNotFoundError
from finance.services.reporter import generate_report, Report
from finance.renderers import (
    RendererNotFoundError, smart_render_strategy
)
from finance.renderers.utils import normalize_output as normalize_renderer_output
from finance.services.report_store.reports import create_cli_artifact
from finance.services.report_store.database import report_database
from finance.services.reporter.repository import get_report_cache_key
from finance.services.email import (
    EmailAttachment,
    EmailException,
    EmailService,
)
from finance.services.report_delivery import render_pdf_attachment
from finance.cli.forms import prompt_signup
from finance.services.watchlist_dispatcher import WatchlistDispatcher


app: Typer = Typer()
account: Typer = Typer(
    name='account',
    help='Account management commands.',
    epilog='Example: python -m finance account <command> [<args>]',
)


def _is_finance_api_process(pid: int) -> bool:
    import psutil

    try:
        arguments: list[str] = [
            argument.casefold()
            for argument in psutil.Process(pid).cmdline()
        ]
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        return False
    has_api_command: bool = (
        'api' in arguments
        and 'serve' in arguments
    )
    return has_api_command or any(
        'api.main:app' in argument
        for argument in arguments
    )


# ================================================== #
# FREQ OPTIONS                                       #
# ================================================== #

AccountEmailOption = Annotated[str, Option(..., '--email', '--account-email', '-e', help='The email of an account')]
AccountNameOption = Annotated[str, Option(..., '--name', '--account-name', '-n', help='The name of an account')]
AccountPasswordOption = Annotated[str, Option(..., '--password', '--account-password', '-p', help='The password of an account')]
ExplainOption = Annotated[bool, Option(..., '--explain', '--ai', '-x', help='Generate an AI explanation for the report')]
ModeOption = Annotated[ReportMode, Option(..., '--mode', '-m', help='Report preset: growth, validation, full, classic, info or custom')]
ChartsOption = Annotated[bool, Option(..., '--charts/--no-charts', '-c', help='Enable charts in the report')]
RendererOption = Annotated[str, Option(..., '--to', '--output', '-o', '--renderer', help='The local output such as a file, console or PDF. You can use "{ticker}", "{date}", "{time}" and "{account}" when it refers a file like "report_{ticker}--{date}.pdf"')]
MachineLearningHorizonOption = Annotated[int, Option(..., '--horizon', '--ml-horizon', '-H', help='The machine learning horizon for predictions')]
VerboseOption = Annotated[bool, Option(..., '--verbose/--quiet', '-v', help='Enable verbose output for debugging purposes')]


# ================================================== #
# FINANCE SCRAPER COMMANDS                           #
# ================================================== #

@app.command(
    name='api',
    help='Run or Close the API server.'
)
def ServeAPI(
    command: Annotated[str, Argument()],
    host: Annotated[str, Option(..., '--host')] = '0.0.0.0',
    port: Annotated[
        int,
        Option(..., '--port', min=1, max=65535),
    ] = 8765,
    pid_file: Annotated[
        Path,
        Option(..., '--pid-file'),
    ] = Path('uvicorn.pid'),
    foreground: Annotated[
        bool,
        Option(..., '--foreground/--background'),
    ] = False,
) -> None:
    import os
    import signal
    from subprocess import Popen

    foreground = foreground or (
        os.getenv('FINANCE_API_FOREGROUND', '').casefold()
        in {'1', 'true', 'yes', 'on'}
    )
    pid_path: Path = pid_file.expanduser().resolve()

    if command.casefold() == 'close':
        if not pid_path.exists():
            console.print('API is not running.')
            return

        pid: int = int(pid_path.read_text(encoding='utf-8'))
        if not _is_finance_api_process(pid):
            pid_path.unlink(missing_ok=True)
            console.print(
                'Stale PID file found; refusing to terminate an unrelated process.',
            )
            return

        token: str | None = os.getenv('FINANCE_DESKTOP_CONTROL_TOKEN')
        shutdown_host: str = (
            '127.0.0.1'
            if host in {'0.0.0.0', '::'}
            else host
        )

        try:
            if token:
                import httpx

                try:
                    response = httpx.post(
                        f'http://{shutdown_host}:{port}/desktop/shutdown',
                        headers={'X-Finance-Desktop-Token': token},
                        timeout=2,
                    )
                    response.raise_for_status()
                    console.print('API shutdown requested.')
                except httpx.HTTPError as e:
                    console.print(f'Graceful API shutdown failed: {e}')
                    os.kill(pid, signal.SIGTERM)
            else:
                os.kill(pid, signal.SIGTERM)
                console.print('API stopped.')
        except ProcessLookupError:
            console.print('Process already dead.')
        finally:
            pid_path.unlink(missing_ok=True)

        return

    if command.casefold() == 'serve':
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        console.print(
            f'API launch mode: {"foreground" if foreground else "background"}',
        )
        if pid_path.exists():
            existing_pid: int = int(
                pid_path.read_text(encoding='utf-8'),
            )
            if _is_finance_api_process(existing_pid):
                console.print(f'API is already running (PID={existing_pid}).')
                return
            pid_path.unlink(missing_ok=True)

        if foreground:
            import uvicorn

            from api.main import app as api_app

            server = uvicorn.Server(
                uvicorn.Config(
                    api_app,
                    host=host,
                    port=port,
                    log_level='info',
                ),
            )
            api_app.state.uvicorn_server = server
            pid_path.write_text(str(os.getpid()), encoding='utf-8')
            try:
                server.run()
            finally:
                pid_path.unlink(missing_ok=True)
            return

        proc = Popen([
            'uvicorn',
            'api.main:app',
            '--host',
            host,
            '--port',
            str(port),
        ])

        pid_path.write_text(str(proc.pid), encoding='utf-8')
        console.print(f'API started (PID={proc.pid})')
        return

    console.print('Use: serve or close')

@app.command(
    name='analyze',
    help='Analyze a stock ticker for a given account email and generate a report.',
    epilog='Example: python -m finance-cli analyze <ticker_symbol> --email <account_email> --name <account_name> --password <account_password> --explain --mode <report_mode> --to <output_filename>'
)
def Analyze(
    requested_symbol: Annotated[str, Argument(help='The stock ticker symbol to analyze')],
    email: AccountEmailOption = None,
    name: AccountNameOption = None,
    password: AccountPasswordOption = None,
    explain: ExplainOption = False,
    mode: ModeOption = ReportMode.CLASSIC,
    charts: ChartsOption = True,
    to: RendererOption = 'console',
    ml_horizon: MachineLearningHorizonOption = 10,
    verbose: VerboseOption = True,
) -> None:
    account: Account | None = account_for_command(
        email=email,
        name=name,
        password=password
    )

    verboser: VerboseSystem = VerboseSystem(verbose)
    
    # fallback to a `default` account if none is provided
    if not account:
        verboser.warning(NO_ACCOUNT_PROVIDED)
        account = asyncio.run(
            get_account_by_name('testing', password='testing')
        )

    # log an error if no account is found after the fallback
    if not account:
        verboser.error(NO_ACCOUNT_FOUND)
        return

    load_i18n(account.language)
    try:
        report: Report = asyncio.run(
            generate_report(
                account,
                Ticker(ticker=requested_symbol),

                generate_explanation=explain,
                generate_charts=charts,
                mode=mode,
                horizon=ml_horizon,
                verbose=verboser.is_verbose
            )
        )

        output: str = to.strip()
        renderer: RendererFactory = smart_render_strategy.match(output.casefold())
        verboser.just_info(
            GENERATING_REPORT.format(
                symbol=requested_symbol,
                renderer=output,
            )
        )
        renderer.render(report, output)
        output_format: str = Path(output).suffix.lower().lstrip('.')
        normalized_output: str | None = None
        if output_format:
            normalized_output = normalize_renderer_output(
                output,
                report,
                output_format,
            )
        elif output.casefold().startswith('pdf'):
            output_format = 'pdf'
            normalized_output = str(renderer.normalize_output(report, output))
        if normalized_output is not None:
            artifact_path: Path = Path(normalized_output)
            if artifact_path.is_file():
                cache_key: str | None = get_report_cache_key(
                    account,
                    report.ticker,
                    generate_explanation=explain,
                    generate_charts=charts,
                    mode=mode,
                    horizon=ml_horizon,
                )
                create_cli_artifact(
                    account_id=str(account.account_id or account.id),
                    resource=report.ticker.ticker,
                    filename=artifact_path.name,
                    report_format=output_format,
                    content_type=(
                        mimetypes.guess_type(artifact_path.name)[0]
                        or 'application/octet-stream'
                    ),
                    artifact=artifact_path.read_bytes(),
                    request={
                        'ticker': report.ticker.ticker,
                        'filename': artifact_path.name,
                        'explain': explain,
                        'mode': mode.value,
                        'charts': charts,
                        'ml_horizon': ml_horizon,
                    },
                    metadata={'generator': 'Analyze'},
                    is_personalized=cache_key is None,
                    cache_key=cache_key,
                )
    
    except TickerNotFoundError as e:    verboser.error(TICKER_NOT_FOUND, expt=e)
    except RendererNotFoundError as e:  verboser.error(RENDERER_NOT_SUPPORTED, expt=e)
    except Exception as e:              
        raise e
        verboser.error(UNKNOWN_ERROR, expt=e())


@app.command(
    name='send',
    help='Generate a PDF report and send it by email.',
    epilog='Example: python -m finance-cli send <ticker> --email <account_email> --password <account_password>',
)
def SendReport(
    requested_symbol: Annotated[str, Argument(help='The stock ticker symbol to generate a report for')],
    email: AccountEmailOption = None,
    password: AccountPasswordOption = None,
    name: AccountNameOption = None,
    explain: ExplainOption = False,
    charts: ChartsOption = False,
    mode: ModeOption = ReportMode.CLASSIC,
    ml_horizon: MachineLearningHorizonOption = 10,
    verbose: VerboseOption = True,
) -> None:
    account: Account | None = account_for_command(
        email=email,
        name=name,
        password=password,
    )

    verboser: VerboseSystem = VerboseSystem(verbose)

    if not account:
        verboser.error(NO_ACCOUNT_FOUND)
        return

    load_i18n(account.language)
    try:
        report: Report = asyncio.run(
            generate_report(
                account,
                Ticker(ticker=requested_symbol),

                generate_explanation=explain,
                generate_charts=charts,
                mode=mode,
                horizon=ml_horizon,
                verbose=verboser.is_verbose,
            )
        )

        verboser.just_info(
            GENERATING_REPORT.format(
                symbol=requested_symbol,
                renderer='pdf',
            )
        )
        attachment_name: str = (
            f'report_{report.ticker.ticker.lower()}--{date.today().isoformat()}.pdf'
        )
        attachment: EmailAttachment = render_pdf_attachment(
            report,
            filename=attachment_name,
        )
        cache_key: str | None = get_report_cache_key(
            account,
            report.ticker,
            generate_explanation=explain,
            generate_charts=charts,
            mode=mode,
            horizon=ml_horizon,
        )
        create_cli_artifact(
            account_id=str(account.account_id or account.id),
            resource=report.ticker.ticker,
            filename=attachment.filename,
            report_format='pdf',
            content_type=f'{attachment.maintype}/{attachment.subtype}',
            artifact=attachment.content,
            request={
                'ticker': report.ticker.ticker,
                'filename': attachment.filename,
                'explain': explain,
                'mode': mode.value,
                'charts': charts,
                'ml_horizon': ml_horizon,
            },
            metadata={'generator': 'SendReport'},
            is_personalized=cache_key is None,
            cache_key=cache_key,
        )
        recipient: str = str(account.email)
        EmailService().send_report_bundle(
            recipient,
            date.today(),
            [report.ticker.symbol],
            [attachment],
        )
        verboser.just_info(
            EMAIL_SENT.format(
                symbol=requested_symbol,
                email=recipient,
            )
        )
    except TickerNotFoundError:
        verboser.error(TICKER_NOT_FOUND)
    except RendererNotFoundError:
        verboser.error(RENDERER_NOT_SUPPORTED)
    except (EmailException, OSError, SMTPException, ValueError) as e:
        verboser.error(EMAIL_DELIVERY_FAILED, expt=e)


@app.command(
    name='dispatch',
    help='Generate and email PDF reports for every account watchlist.',
    epilog='Example: python -m finance-cli dispatch',
)
def DispatchReports(verbose: VerboseOption = True) -> None:
    """Run the stateless watchlist dispatcher from an external scheduler."""

    verboser: VerboseSystem = VerboseSystem(verbose)
    try:
        results = asyncio.run(WatchlistDispatcher().dispatch_all_accounts())
    except (EmailException, OSError, SMTPException, ValueError) as e:
        verboser.error(EMAIL_DELIVERY_FAILED, expt=e)
        return
    finally:
        asyncio.run(sync_and_close_database_pools())

    for result in results:
        if result.email_sent:
            verboser.info(
                f'{result.account_email}: sent '
                f'{len(result.generated_tickers)} PDF report(s).'
            )
            continue
        if result.error:
            verboser.error(
                f'{result.account_email}: {result.error}'
            )
            continue
        verboser.warning(
            f'{result.account_email}: no enabled watchlist reports.'
        )



@app.command(
    name='signup',
    help='Sign up a new account.',
    epilog='Example: python -m finance-cli account signup'
)
def SignUp(verbose: VerboseOption = True) -> None:
    return AccountSignUp(verbose)


def _legacy_account_for_command(
    email: str | None,
    name: str | None,
    password: str | None,
) -> Account | None:
    if not password:
        return None
    return get_account(email=email, name=name, password=password)


def account_for_command(
    email: str | None,
    name: str | None,
    password: str | None,
) -> Account | None:
    if not password:
        return None
    return asyncio.run(
        get_account(
            email=email,
            name=name,
            password=password,
        )
    )


@account.command(name='languages', help='List all available languages.')
def AccountLanguages() -> None:
    for language in get_available_languages():
        console.print(f'{language.code}: {language.name}')


@account.command(name='styles', help='List all available language styles.')
def AccountStyles() -> None:
    for style in get_available_language_styles():
        console.print(style)


@account.command(name='modes', help='List all available report modes.')
def AccountModes() -> None:
    for mode in get_available_report_modes():
        console.print(mode.value)


@account.command(name='signup', help='Sign up a new account.')
def AccountSignUp(verbose: VerboseOption = True) -> None:
    verboser: VerboseSystem = VerboseSystem(verbose, is_dev=IS_DEV)
    try:
        form = prompt_signup()
    except ValueError as e:
        verboser.error(str(e))
        return
    if form is None:
        verboser.error('Signup was cancelled.')
        return

    watchlist: list[WatchlistItem] = [
        WatchlistItem(
            ticker=Ticker(ticker=symbol).symbol,
            region=Ticker(ticker=symbol).region,
        )
        for symbol in form.watchlist_symbols
    ]

    account_data = Account(
        name=form.name,
        email=form.email,
        language=form.language.model_copy(update={'style': form.style}),
        watchlist=watchlist,
    )
    try:
        asyncio.run(create_account(account_data, form.password))
    except AccountAlreadyExistsError:
        verboser.error(ACCOUNT_ALREADY_EXISTS.format(email=form.email))
        return
    verboser.info(f'Account {form.email} created successfully.')


@account.command(name='show', help='Show account details.')
def AccountShow(
    email: AccountEmailOption = None,
    name: AccountNameOption = None,
    password: AccountPasswordOption = None,
) -> None:
    account_data: Account | None = account_for_command(email, name, password)
    if account_data is None:
        console.print('Account not found or password is missing.')
        return
    console.print(account_data.model_dump_json(indent=2))


@account.command(name='add', help='Add a ticker to your watchlist.')
def AccountAdd(
    ticker: Annotated[str, Argument(help='Ticker symbol to add')],
    email: AccountEmailOption = None,
    name: AccountNameOption = None,
    password: AccountPasswordOption = None,
    mode: ModeOption = ReportMode.CLASSIC,
    explain: ExplainOption = False,
    charts: ChartsOption = True,
    ml_horizon: MachineLearningHorizonOption = 10,
) -> None:
    account_data: Account | None = account_for_command(email, name, password)
    if account_data is None:
        console.print('Account not found or password is missing.')
        return
    try:
        normalized_ticker: Ticker = Ticker(ticker=ticker)
        item = WatchlistItem(
            ticker=normalized_ticker.symbol,
            region=normalized_ticker.region,
            mode=mode,
            llm_explanation=explain,
            charts=charts,
            horizon=ml_horizon,
        )
        asyncio.run(add_watchlist_item(account_data, item))
    except ValueError as e:
        console.print(str(e))
        return
    console.print(TICKER_ADDED_TO_WATCHLIST.format(
        ticker=item.symbol,
        account=account_data.email,
    ))


@account.command(name='remove', help='Remove a ticker from your watchlist.')
def AccountRemove(
    ticker: Annotated[str, Argument(help='Ticker symbol to remove')],
    email: AccountEmailOption = None,
    name: AccountNameOption = None,
    password: AccountPasswordOption = None,
) -> None:
    account_data: Account | None = account_for_command(email, name, password)
    if account_data is None:
        console.print('Account not found or password is missing.')
        return
    try:
        normalized_ticker: Ticker = Ticker(ticker=ticker)
        asyncio.run(
            remove_watchlist_item(account_data, normalized_ticker.symbol)
        )
    except ValueError as e:
        console.print(str(e))
        return
    console.print(f'{normalized_ticker.symbol} was removed from the watchlist.')


def add_account_trade(
    action: str,
    ticker: str,
    email: str | None,
    name: str | None,
    password: str | None,
    currency: str,
    region: str,
    price: float,
    quantity: int,
    trade_date: str,
) -> None:
    account_data: Account | None = account_for_command(email, name, password)
    if account_data is None:
        console.print('Account not found or password is missing.')
        return
    try:
        normalized_ticker: Ticker = Ticker(ticker=ticker)
        asyncio.run(
            add_trade(
                account_data,
                action,
                normalized_ticker.symbol,
                region.upper(),
                currency.upper(),
                price,
                quantity,
                trade_date,
            )
        )
    except ValueError as e:
        console.print(str(e))
        return
    console.print(
        f'{action} {quantity} shares of {normalized_ticker.symbol} recorded.'
    )


@account.command(name='buy', help='Record a buy trade for your account.')
def AccountBuy(
    ticker: Annotated[str, Argument(help='Ticker symbol to buy')],
    price: Annotated[float, Option(help='Price per share')],
    quantity: Annotated[int, Option(help='Share quantity')],
    currency: Annotated[str, Option(help='Trade currency')] = 'USD',
    region: Annotated[str, Option(help='Market region')] = 'US',
    trade_date: Annotated[str | None, Option(help='Trade date, YYYY-MM-DD')] = None,
    email: AccountEmailOption = None,
    name: AccountNameOption = None,
    password: AccountPasswordOption = None,
) -> None:
    add_account_trade(
        'BUY',
        ticker,
        email,
        name,
        password,
        currency,
        region,
        price,
        quantity,
        trade_date or date.today().isoformat(),
    )


@account.command(name='sell', help='Record a sell trade for your account.')
def AccountSell(
    ticker: Annotated[str, Argument(help='Ticker symbol to sell')],
    price: Annotated[float, Option(help='Price per share')],
    quantity: Annotated[int, Option(help='Share quantity')],
    currency: Annotated[str, Option(help='Trade currency')] = 'USD',
    region: Annotated[str, Option(help='Market region')] = 'US',
    trade_date: Annotated[str | None, Option(help='Trade date, YYYY-MM-DD')] = None,
    email: AccountEmailOption = None,
    name: AccountNameOption = None,
    password: AccountPasswordOption = None,
) -> None:
    add_account_trade(
        'SELL',
        ticker,
        email,
        name,
        password,
        currency,
        region,
        price,
        quantity,
        trade_date or date.today().isoformat(),
    )


@account.command(name='portfolio', help='View your account portfolio.')
def AccountPortfolio(
    email: AccountEmailOption = None,
    name: AccountNameOption = None,
    password: AccountPasswordOption = None,
) -> None:
    account_data: Account | None = account_for_command(email, name, password)
    if account_data is None:
        console.print('Account not found or password is missing.')
        return
    table = Table('Ticker', 'Region', 'Currency', 'Action', 'Quantity', 'Price', 'Date')
    for stock in account_data.portfolio:
        if not isinstance(stock, Stock):
            continue
        for action in stock.actions:
            table.add_row(
                stock.ticker,
                stock.region,
                stock.currency,
                action.action,
                str(action.quantity),
                str(action.price),
                action.date,
            )
    console.print(table)


app.add_typer(account)


def main() -> None:
    try:
        app()
    finally:
        try:
            report_database.close()
        finally:
            asyncio.run(sync_and_close_database_pools())


if __name__ == '__main__':
    main()
