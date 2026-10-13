
from typing import Any, Callable

from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.segment import Segment
from rich.align import Align
from rich.padding import Padding
from rich.console import Group, RenderableType
from rich.columns import Columns
from rich import box

from datatypes import Money, Ticker
from finance import investopedia_links as wiki
from finance.config import console
from finance.types import Language, ReportPreset, get_preset
from finance.services.reporter import Report
from finance.services.stock_analyzer import DescriptiveFacts, QuantifiableFacts, StockAnalysis
from finance.services.stock_analyzer.models import Fact, Metric, MetricGrade
from finance.services.llm.models import Explanation, Reasoning
from finance.services.ml import PredictionResult
from finance.services.i18n import i18n
from finance.services.i18n.models import Translation

from finance.renderers.console import fmt



# ================================================== #
# HELPER FUNCTIONS                                   #
# ================================================== #

def _translation(report: Report, mnemonic: str, fallback: str, field: str = 'title') -> str:
    language: Language = report.account.language
    snapshot: Translation = i18n(
        f'analyzer.{mnemonic}',
        language,
        throw_error=False,
    )('.', throw_error=False)

    value: str | None = getattr(snapshot, field, None)
    return value or fallback


def _section_title(report: Report, mnemonic: str, fallback: str) -> str:
    title: str = _translation(report, mnemonic, fallback)
    description: str = _translation(report, mnemonic, '', field='description')
    return f'{title} [dim]({description})[/dim]' if description else title


def _metric_panel(
    report: Report,
    metric: Metric,
    mnemonic: str,
    fallback: str,
    fmt_func: Callable[[Metric], str],
    *,
    link_url: str | None = None,
    show_rating: bool = True,
) -> Panel | None:
    if report.mode.value == 'custom':
        requested: set[str] = {
            item.strip().lower()
            for item in report.custom_report
        }
        short_mnemonic: str = mnemonic.rsplit('.', 1)[-1]
        section: str = mnemonic.split('.', 1)[0]
        aliases: set[str] = {short_mnemonic.lower()}
        if short_mnemonic == 'ev2market_cap':
            aliases.add('ev_to_market_cap')
        if (
            mnemonic.lower() not in requested
            and not aliases.intersection(requested)
            and section.lower() not in requested
        ):
            return None

    title: str = _translation(report, mnemonic, fallback)
    return Panel(
        fmt.as_table(
            metric,
            title if link_url is None else fmt.as_lowkey_link(title, link_url),
            fmt_func,
            show_rating=show_rating,
        ),
        title=title,
    )


def _metric_section(panels: list[Panel | None], columns: int) -> Table | None:
    visible: list[Panel] = [panel for panel in panels if panel is not None]
    if not visible:
        return None

    section: Table = Table.grid(expand=True)
    for index in range(0, len(visible), columns):
        section.add_row(*visible[index:index + columns])
    return section


def _custom_feature_requested(report: Report, feature: str) -> bool:
    if report.mode.value != 'custom':
        return True

    requested: set[str] = {
        item.strip().lower()
        for item in report.custom_report
    }
    if feature == 'dividends_and_splits':
        return bool(requested.intersection({'dividends_and_splits', 'dividends', 'splits'}))
    return feature in requested



# ================================================== #
# REPORT SECTION RENDERERS                           #
# ================================================== #

def _header(report: Report) -> Group:
    ticker: Ticker = report.ticker
    quantifiable_f: QuantifiableFacts = report.analysis.quantifiable_facts
    descriptive_f: DescriptiveFacts = report.analysis.descriptive_facts

    grid: Table = Table.grid(expand=True)
    grid.add_column()
    grid.add_column(justify='right')

    grid.add_row(
        f'[bold]{ticker.symbol}[/bold] [{ticker.region}]',
        (
            f'{
                fmt.as_link(
                    text='GBM',
                    url=f'https://www.appgbm.com/market/details/offshore/{ticker.symbol}'
                )
            }'
            ' | '
            f'{
                fmt.as_link(
                    text='TradingView',
                    url=f'https://www.tradingview.com/symbols/{ticker.symbol}/'
                )
            }'

        )
    )
    grid.add_row(
        fmt.as_text(descriptive_f.name),
        fmt.with_percentage(
            formatted=fmt.as_price(
                metric=quantifiable_f.price
            ),
            metric=quantifiable_f.price,
        )
    )

    return Group(
        grid
    )

def _llm_and_ml_prediction(report: Report) -> Group:
    prediction_result: PredictionResult = report.prediction_result
    explanation: Explanation | None = report.explanation

    formatted_points: list[str] = []
    for point in explanation.points if explanation else []:
        try:
            formatted_points.append(fmt.as_point(point.reasoning, point.content))
        except ValueError as e:
            formatted_points.append(f'[dim italic]\\[?] {point.content}[/dim italic]')

    no_points: str = _translation(report, 'prediction_empty', 'No points available.')
    formatted_ml_results: str = ' | '.join([
        f'[dim]{possible_action.action.value.upper()}: [bold]{possible_action.probability:.2f}[/bold][/dim]'
        for possible_action in prediction_result.action_probabilities
    ])
    grid: Table = Table.grid(expand=True)
    grid.add_row(
        Padding(
            fmt.justify(
                fmt.as_text(formatted_ml_results) +
                f'\n{"[dim]─[/dim]"*(console.width - 6)}\n' +
                (explanation.summary if explanation else 'N/A') +
                '\n\n' +
                (
                    ''.join(point + '\n' for point in formatted_points) if formatted_points else f'[dim italic]{no_points}[/dim italic]'
                )
            ),
            (1, 1)
        )
    )

    return Group(
        grid
    )

def _analysis(report: Report) -> Group:
    analysis: StockAnalysis = report.analysis

    valuation_metrics: list[Panel | None] = [
        _metric_panel(report, analysis.valuation.pe_ratio, 'valuation.pe_ratio', 'P/E Ratio', fmt.as_multiple, link_url=wiki.PE_RATIO_LINK),
        _metric_panel(report, analysis.valuation.peg_ratio, 'valuation.peg_ratio', 'PEG Ratio', fmt.as_multiple, link_url=wiki.PEG_RATIO_LINK),
        _metric_panel(report, analysis.valuation.trailing_pe_ratio, 'valuation.trailing_pe_ratio', 'Trailing P/E', fmt.as_multiple, link_url=wiki.PE_RATIO_LINK),
        _metric_panel(report, analysis.valuation.forward_pe_ratio, 'valuation.forward_pe_ratio', 'Forward P/E', fmt.as_multiple, link_url=wiki.PE_RATIO_LINK),
        _metric_panel(report, analysis.valuation.ev_to_market_cap, 'valuation.ev2market_cap', 'EV/Market Cap', fmt.as_multiple, link_url=wiki.EV_TO_MARKET_CAP_LINK),
        _metric_panel(report, analysis.valuation.price_to_fcf, 'valuation.price_to_fcf', 'Price/FCF', fmt.as_multiple, link_url=wiki.FREE_CASH_FLOW_LINK),
        _metric_panel(report, analysis.valuation.ev_to_ebitda, 'valuation.ev_to_ebitda', 'EV/EBITDA', fmt.as_multiple, link_url=wiki.EV_TO_EBITDA_LINK),
        _metric_panel(report, analysis.valuation.earnings_yield, 'valuation.earnings_yield', 'Earnings Yield', fmt.as_percent, link_url=wiki.EARNINGS_YIELD_LINK),
    ]
    if report.mode.value == 'custom':
        valuation_metrics.extend(
            [
                _metric_panel(report, analysis.valuation.ev_to_ebit, 'valuation.ev_to_ebit', 'EV/EBIT', fmt.as_multiple, link_url=wiki.EV_TO_EBIT_LINK),
                _metric_panel(report, analysis.valuation.price_to_book, 'valuation.price_to_book', 'Price/Book', fmt.as_multiple, link_url=wiki.PRICE_TO_BOOK_LINK),
                _metric_panel(report, analysis.valuation.price_to_sales, 'valuation.price_to_sales', 'Price/Sales', fmt.as_multiple, link_url=wiki.PRICE_TO_SALES_LINK),
            ]
        )
    valuation: Table | None = _metric_section(valuation_metrics, columns=4)

    growth_metrics: list[Panel | None] = [
        _metric_panel(report, analysis.growth.revenue_growth, 'growth.revenue_growth', 'Revenue Growth', fmt.as_percent, link_url=wiki.REVENUE_GROWTH_LINK),
        _metric_panel(report, analysis.growth.earnings_growth, 'growth.earnings_growth', 'Earnings Growth', fmt.as_percent, link_url=wiki.EARNINGS_GROWTH_LINK),
        _metric_panel(report, analysis.growth.eps_growth, 'growth.eps_growth', 'EPS Growth', fmt.as_percent, link_url=wiki.EPS_GROWTH_LINK),
        _metric_panel(report, analysis.growth.revenue_cagr_5y, 'growth.revenue_cagr_5y', 'Revenue CAGR 5Y', fmt.as_percent, link_url=wiki.REVENUE_CAGR_LINK),
        _metric_panel(report, analysis.growth.eps_cagr_5y, 'growth.eps_cagr_5y', 'EPS CAGR 5Y', fmt.as_percent, link_url=wiki.EPS_CAGR_LINK),
        _metric_panel(report, analysis.growth.fcf_cagr_5y, 'growth.fcf_cagr_5y', 'FCF CAGR 5Y', fmt.as_percent, link_url=wiki.FCF_CAGR_LINK),
    ]
    if report.mode.value == 'custom':
        growth_metrics.extend(
            [
                _metric_panel(report, analysis.growth.revenue_cagr_10y, 'growth.revenue_cagr_10y', 'Revenue CAGR 10Y', fmt.as_percent, link_url=wiki.REVENUE_CAGR_LINK),
                _metric_panel(report, analysis.growth.eps_cagr_10y, 'growth.eps_cagr_10y', 'EPS CAGR 10Y', fmt.as_percent, link_url=wiki.EPS_CAGR_LINK),
                _metric_panel(report, analysis.growth.fcf_cagr_10y, 'growth.fcf_cagr_10y', 'FCF CAGR 10Y', fmt.as_percent, link_url=wiki.FCF_CAGR_LINK),
                _metric_panel(report, analysis.growth.fcf_growth, 'growth.fcf_growth', 'FCF Growth', fmt.as_percent, link_url=wiki.FCF_GROWTH_LINK),
                _metric_panel(report, analysis.growth.owner_earnings_growth, 'growth.owner_earnings_growth', 'Owner Earnings Growth', fmt.as_percent, link_url=wiki.OWNER_EARNINGS_GROWTH_LINK),
                _metric_panel(report, analysis.growth.shares_outstanding_growth, 'growth.shares_outstanding_growth', 'Shares Outstanding Growth', fmt.as_percent, link_url=wiki.SHARES_OUTSTANDING_GROWTH_LINK),
                _metric_panel(report, analysis.growth.retained_earnings_growth, 'growth.retained_earnings_growth', 'Retained Earnings Growth', fmt.as_percent, link_url=wiki.RETAINED_EARNINGS_GROWTH_LINK),
            ]
        )
    growth: Table | None = _metric_section(growth_metrics, columns=3)

    profitability_metrics: list[Panel | None] = [
        _metric_panel(report, analysis.profitability.return_on_equity, 'profitability.return_on_equity', 'ROE', fmt.as_percent, link_url=wiki.RETURN_ON_EQUITY_LINK),
        _metric_panel(report, analysis.profitability.return_on_assets, 'profitability.return_on_assets', 'ROA', fmt.as_percent, link_url=wiki.RETURN_ON_ASSETS_LINK),
        _metric_panel(report, analysis.profitability.roic, 'profitability.roic', 'ROIC', fmt.as_percent, link_url=wiki.ROIC_LINK),
        _metric_panel(report, analysis.profitability.roce, 'profitability.roce', 'ROCE', fmt.as_percent, link_url=wiki.ROCE_LINK),
        _metric_panel(report, analysis.profitability.gross_margin, 'profitability.gross_margin', 'Gross Margin', fmt.as_percent, link_url=wiki.GROSS_MARGIN_LINK),
        _metric_panel(report, analysis.profitability.ebitda_margin, 'profitability.ebitda_margin', 'EBITDA Margin', fmt.as_percent, link_url=wiki.EBITDA_MARGIN_LINK),
    ]
    if report.mode.value == 'custom':
        profitability_metrics.extend(
            [
                _metric_panel(report, analysis.profitability.return_on_equity_5y, 'profitability.return_on_equity_5y', 'Average ROE 5Y', fmt.as_percent, link_url=wiki.RETURN_ON_EQUITY_LINK),
                _metric_panel(report, analysis.profitability.return_on_equity_10y, 'profitability.return_on_equity_10y', 'Average ROE 10Y', fmt.as_percent, link_url=wiki.RETURN_ON_EQUITY_LINK),
                _metric_panel(report, analysis.profitability.gross_profit, 'profitability.gross_profit', 'Gross Profit', lambda m: fmt.as_currency(m), link_url=wiki.GROSS_PROFIT_LINK),
                _metric_panel(report, analysis.profitability.ebitda, 'profitability.ebitda', 'EBITDA', lambda m: fmt.as_currency(m), link_url=wiki.EBITDA_LINK),
            ]
        )
    profitability: Table | None = _metric_section(profitability_metrics, columns=3)

    cash_flow_metrics: list[Panel | None] = [
        _metric_panel(
            report,
            analysis.cash_flow.operating_cash_flow,
            'cash_flow.operating_cash_flow',
            'Operating Cash Flow',
            lambda m: fmt.as_currency(m),
            show_rating=True,
            link_url=wiki.OPERATING_CASH_FLOW_LINK
        ),
        _metric_panel(
            report,
            analysis.cash_flow.owner_earnings,
            'cash_flow.owner_earnings',
            'Owner Earnings*',
            lambda m: fmt.as_currency(m),
            show_rating=True,
            link_url=wiki.OWNER_EARNINGS_LINK
        ),
        _metric_panel(report, analysis.cash_flow.fcf_margin, 'cash_flow.fcf_margin', 'FCF Margin', fmt.as_percent, link_url=wiki.FREE_CASH_FLOW_MARGIN_LINK),
        _metric_panel(report, analysis.cash_flow.operating_cash_flow_margin, 'cash_flow.operating_cash_flow_margin', 'OCF Margin', fmt.as_percent, link_url=wiki.OPERATING_CASH_FLOW_MARGIN_LINK),
        _metric_panel(report, analysis.cash_flow.cash_conversion, 'cash_flow.cash_conversion', 'Cash Conversion', fmt.as_multiple, link_url=wiki.CASH_CONVERSION_LINK),
        _metric_panel(report, analysis.cash_flow.owner_earnings_yield, 'cash_flow.owner_earnings_yield', 'Owner Earnings Yield', fmt.as_percent, link_url=wiki.OWNER_EARNINGS_YIELD_LINK),
    ]
    if report.mode.value == 'custom':
        cash_flow_metrics.append(
            _metric_panel(
                report,
                analysis.cash_flow.capital_expenditures,
                'cash_flow.capital_expenditures',
                'Capital Expenditures',
                lambda m: fmt.as_currency(m),
            )
        )
    cash_flow: Table | None = _metric_section(cash_flow_metrics, columns=3)

    financial_health_metrics: list[Panel | None] = [
        _metric_panel(report, analysis.financial_health.debt_to_equity, 'financial_health.debt_to_equity', 'Debt/Equity', lambda m: fmt.as_number(m, ndigits=2), link_url=wiki.DEBT_TO_EQUITY_LINK),
        _metric_panel(report, analysis.financial_health.current_ratio, 'financial_health.current_ratio', 'Current Ratio', lambda m: fmt.as_number(m, ndigits=2), link_url=wiki.CURRENT_RATIO_LINK),
        _metric_panel(report, analysis.financial_health.quick_ratio, 'financial_health.quick_ratio', 'Quick Ratio', lambda m: fmt.as_number(m, ndigits=2), link_url=wiki.QUICK_RATIO_LINK),
        _metric_panel(report, analysis.financial_health.net_debt, 'financial_health.net_debt', 'Net Debt', lambda m: fmt.as_currency(m), link_url=wiki.NET_DEBT_LINK),
        _metric_panel(report, analysis.financial_health.net_debt_to_ebitda, 'financial_health.net_debt_to_ebitda', 'Net Debt/EBITDA', fmt.as_multiple, link_url=wiki.NET_DEBT_TO_EBITDA_LINK),
    ]
    if report.mode.value == 'custom':
        financial_health_metrics.append(
            _metric_panel(
                report,
                analysis.financial_health.free_cash_flow,
                'financial_health.free_cash_flow',
                'Free Cash Flow',
                lambda m: fmt.as_currency(m),
                link_url=wiki.FREE_CASH_FLOW_LINK
            )
        )
    financial_health: Table | None = _metric_section(financial_health_metrics, columns=5)

    capital_allocation_metrics: list[Panel | None] = [
        _metric_panel(report, analysis.capital_allocation.shares_outstanding, 'capital_allocation.shares_outstanding', 'Shares Outstanding', fmt.as_integer, link_url=wiki.SHARES_OUTSTANDING_LINK),
        _metric_panel(report, analysis.capital_allocation.buyback_yield, 'capital_allocation.buyback_yield', 'Buyback Yield', fmt.as_percent, link_url=wiki.BUYBACK_YIELD_LINK),
        _metric_panel(report, analysis.capital_allocation.shareholder_yield, 'capital_allocation.shareholder_yield', 'Shareholder Yield', fmt.as_percent, link_url=wiki.SHAREHOLDER_YIELD_LINK),
        _metric_panel(report, analysis.capital_allocation.retained_earnings, 'capital_allocation.retained_earnings', 'Retained Earnings', lambda m: fmt.as_currency(m), link_url=wiki.RETAINED_EARNINGS_LINK),
        _metric_panel(report, analysis.capital_allocation.acquisition_spending, 'capital_allocation.acquisition_spending', 'Acquisition Spending', lambda m: fmt.as_currency(m), link_url=wiki.ACQUISITION_SPENDING_LINK),
    ]
    capital_allocation: Table | None = _metric_section(capital_allocation_metrics, columns=5)

    working_capital_metrics: list[Panel | None] = [
        _metric_panel(report, analysis.working_capital.working_capital, 'working_capital.working_capital', 'Working Capital', lambda m: fmt.as_currency(m), link_url=wiki.WORKING_CAPITAL_LINK),
        _metric_panel(report, analysis.working_capital.change_in_working_capital, 'working_capital.change_in_working_capital', 'Change in WC', lambda m: fmt.as_currency(m), link_url=wiki.CHANGE_IN_WORKING_CAPITAL_LINK),
        _metric_panel(report, analysis.working_capital.receivables, 'working_capital.receivables', 'Receivables', lambda m: fmt.as_currency(m), link_url=wiki.RECEIVABLES_LINK),
        _metric_panel(report, analysis.working_capital.inventory, 'working_capital.inventory', 'Inventory', lambda m: fmt.as_currency(m), link_url=wiki.INVENTORY_LINK),
        _metric_panel(report, analysis.working_capital.accounts_payable, 'working_capital.accounts_payable', 'Accounts Payable', lambda m: fmt.as_currency(m), link_url=wiki.ACCOUNTS_PAYABLE_LINK),
    ]
    working_capital: Table | None = _metric_section(working_capital_metrics, columns=5)

    sections: list[tuple[str, Table | None, str]] = [
        ('valuation', valuation, 'Valuation'),
        ('profitability', profitability, 'Profitability'),
        ('cash_flow', cash_flow, 'Cash Flow'),
        ('growth', growth, 'Growth'),
        ('financial_health', financial_health, 'Financial Health'),
        ('capital_allocation', capital_allocation, 'Capital Allocation'),
        ('working_capital', working_capital, 'Working Capital'),
    ]
    preset: ReportPreset = get_preset(report.mode)
    return Group(
        *[
            Panel(section, title=_section_title(report, mnemonic, fallback))
            for mnemonic, section, fallback in sections
            if mnemonic in preset.sections and section is not None
        ]
    )

def _dividends_and_splits(report: Report) -> Group:
    quantifiable_f: QuantifiableFacts = report.analysis.quantifiable_facts
    descriptive_f: DescriptiveFacts = report.analysis.descriptive_facts

    dividends: Table = Table.grid(expand=True)
    dividends.add_row(
        fmt.as_text(f'{_translation(report, 'fact.dividend_yield', 'Dividend Yield')}:'),
        fmt.as_percent(quantifiable_f.dividend_yield)
    )
    dividends.add_row(
        fmt.as_text(f'{_translation(report, 'fact.dividend_rate', 'Dividend Rate')}:'),
        fmt.as_currency(quantifiable_f.dividend_rate)
    )
    dividends.add_row(
        fmt.as_text(f'{_translation(report, 'fact.last_dividend', 'Last Dividend')}:'),
        fmt.as_currency(Metric(metric=descriptive_f.last_dividend.value))
        if isinstance(descriptive_f.last_dividend.value, Money)
        else fmt.as_text(descriptive_f.last_dividend)
    )

    splits: Table = Table.grid(expand=True)
    splits.add_row(
        fmt.as_text(f'{_translation(report, 'fact.splits', 'Splits')}:'),
        fmt.as_text(descriptive_f.splits),
    )

    container: Table = Table.grid(expand=True)
    container.add_column(ratio=1)
    container.add_column(ratio=1)
    container.add_row(dividends, splits)

    return Group(
        container
    )

def _description(report: Report) -> Group:
    descriptive_f: DescriptiveFacts = report.analysis.descriptive_facts

    grid: Table = Table.grid(expand=True)
    grid.add_row(
        Padding(
            fmt.justify(
                fmt.as_text(descriptive_f.description) +
                '\n\n' +
                (
                    fmt.as_link(
                        text=descriptive_f.website,
                        url=descriptive_f.website,
                    )
                    if descriptive_f.website
                    else f'[dim italic]{_translation(report, 'business_summary.no_website', 'No website available.')}[/dim italic]'
                )
            ),
            (1, 1)
        )
    )

    return Group(
        grid
    )


def _news(report: Report) -> Group:
    content: str = report.get_news() or 'N/A'
    return Group(
        Padding(fmt.as_text(content), (1, 1))
    )



# ================================================== #
# REPORT RENDERER                                    #
# ================================================== #

class ConsoleRenderer:
    def __init__(self, *args: Any, **kwargs: dict[str, Any]) -> None:
        self.args = args
        self.kwargs = kwargs

    def render(self, report: Report, output: str | None = None) -> None:
        preset: ReportPreset = get_preset(report.mode)
        header: Group = _header(report)
        renderables: list[RenderableType] = [Panel(header)]

        if preset.show_explanation and _custom_feature_requested(report, 'explanation'):
            renderables.append(Panel(_llm_and_ml_prediction(report), title=_translation(report, 'prediction', 'AI Generated Prediction')))
            renderables.append('\n')
        if preset.show_analysis:
            renderables.append(_analysis(report))
            renderables.append('\n')
        if preset.show_facts and _custom_feature_requested(report, 'dividends_and_splits'):
            renderables.append(Panel(_dividends_and_splits(report), title=_translation(report, 'dividends_and_splits', 'Dividends and Splits')))
            renderables.append('\n')
        if preset.show_news:
            renderables.append(Panel(_news(report), title=_translation(report, 'recent_news', 'Recent News')))
            renderables.append('\n')
        if preset.show_description: renderables.append(Panel(_description(report), title=_translation(report, 'business_summary', 'Business Summary')))

        report_group: Group = Group(*renderables)
        
        console.print(report_group)
