
import re
from decimal import Decimal
from datetime import date

from datatypes import Money, YFinanceStatement, YFinanceTickerInfo
from finance.services.stock_analyzer.models import Metric, MetricEvaluator
from finance.services.stock_analyzer.utils import (
    NONE_EVALUATOR,
    money_metric,
    verify_availability,
)


def _metric(value: float | int | None, info: YFinanceTickerInfo) -> Metric:
    metric = Metric(metric=float(value) if isinstance(value, (int, float)) else None)
    verify_availability(metric, info)
    return metric


def _amount(value: float | int | Decimal | Money | None) -> float | None:
    if isinstance(value, Money):
        return float(value.value)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _normalized_label(value: str) -> str:
    return re.sub(r'[^a-z0-9]', '', value.lower())


def _row(statement: YFinanceStatement, aliases: tuple[str, ...]) -> dict[str, int | float | None]:
    rows = {
        _normalized_label(name): values
        for name, values in statement.values.items()
    }
    for alias in aliases:
        found = rows.get(_normalized_label(alias))
        if found is not None:
            return found
    return {}


def _latest(statement: YFinanceStatement, aliases: tuple[str, ...]) -> float | None:
    values = _row(statement, aliases)
    for period in sorted(values, reverse=True):
        value = values[period]
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _series(statement: YFinanceStatement, aliases: tuple[str, ...]) -> list[tuple[date, float]]:
    values = _row(statement, aliases)
    result: list[tuple[date, float]] = []
    for period, value in values.items():
        if not isinstance(value, (int, float)):
            continue
        try:
            result.append((date.fromisoformat(period[:10]), float(value)))
        except ValueError:
            continue
    return sorted(result)


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _cagr(statement: YFinanceStatement, aliases: tuple[str, ...], years: int) -> float | None:
    values = _series(statement, aliases)
    if len(values) < 2:
        return None

    latest_date, latest_value = values[-1]
    candidates = [
        (period, value)
        for period, value in values[:-1]
        if (latest_date - period).days >= years * 365
    ]
    if not candidates or latest_value <= 0:
        return None

    start_date, start_value = candidates[-1]
    if start_value <= 0:
        return None

    elapsed_years = (latest_date - start_date).days / 365.25
    if elapsed_years <= 0:
        return None
    return (latest_value / start_value) ** (1 / elapsed_years) - 1


def _average_return(
    info: YFinanceTickerInfo,
    numerator_aliases: tuple[str, ...],
    denominator_aliases: tuple[str, ...],
    years: int,
) -> float | None:
    numerators = dict(_series(info.incomeStatement, numerator_aliases))
    denominators = dict(_series(info.balanceSheet, denominator_aliases))
    observations = [
        numerators[period] / denominator
        for period, denominator in denominators.items()
        if denominator != 0 and period in numerators
    ]
    if len(observations) < years:
        return None
    return sum(observations[-years:]) / years


def _cash_flow(info: YFinanceTickerInfo) -> float | None:
    return info.operatingCashflow or _latest(
        info.cashFlow,
        ('Operating Cash Flow', 'Total Cash From Operating Activities'),
    )


def _capex(info: YFinanceTickerInfo) -> float | None:
    return _latest(
        info.cashFlow,
        ('Capital Expenditure', 'Capital Expenditures', 'Purchase Of Property Plant And Equipment'),
    )


def _free_cash_flow(info: YFinanceTickerInfo) -> float | None:
    if info.freeCashflow is not None:
        return info.freeCashflow
    operating_cash_flow = _cash_flow(info)
    capital_expenditures = _capex(info)
    if operating_cash_flow is None or capital_expenditures is None:
        return None
    return operating_cash_flow + capital_expenditures


def _current_assets(info: YFinanceTickerInfo) -> float | None:
    return _latest(info.balanceSheet, ('Current Assets', 'Total Current Assets'))


def _current_liabilities(info: YFinanceTickerInfo) -> float | None:
    return _latest(info.balanceSheet, ('Current Liabilities', 'Total Current Liabilities'))


def _market_cap(info: YFinanceTickerInfo) -> float | None:
    return float(info.marketCap) if info.marketCap is not None else None


def _enterprise_value(info: YFinanceTickerInfo) -> float | None:
    return float(info.enterpriseValue) if info.enterpriseValue is not None else None


def price_to_fcf(info: YFinanceTickerInfo) -> Metric:
    return _metric(_ratio(_market_cap(info), _free_cash_flow(info)), info)


def ev_to_ebitda(info: YFinanceTickerInfo) -> Metric:
    value = info.enterpriseToEbitda
    if value is None:
        value = _ratio(_enterprise_value(info), info.ebitda or _latest(info.incomeStatement, ('EBITDA',)))
    return _metric(value, info)


def ev_to_ebit(info: YFinanceTickerInfo) -> Metric:
    ebit = _latest(info.incomeStatement, ('Operating Income', 'EBIT'))
    return _metric(_ratio(_enterprise_value(info), ebit), info)


def price_to_book(info: YFinanceTickerInfo) -> Metric:
    return _metric(info.priceToBook, info)


def price_to_sales(info: YFinanceTickerInfo) -> Metric:
    return _metric(info.priceToSalesTrailing12Months, info)


def earnings_yield(info: YFinanceTickerInfo) -> Metric:
    value = _ratio(info.trailingEps, info.currentPrice)
    if value is None and info.trailingPE not in (None, 0):
        value = 1 / info.trailingPE
    return _metric(value, info)


def roic(info: YFinanceTickerInfo) -> Metric:
    ebit = _latest(info.incomeStatement, ('Operating Income', 'EBIT'))
    pretax_income = _latest(info.incomeStatement, ('Pretax Income', 'Income Before Tax'))
    tax_provision = _latest(info.incomeStatement, ('Tax Provision', 'Income Tax Expense'))
    total_debt = float(info.totalDebt) if info.totalDebt is not None else _latest(
        info.balanceSheet,
        ('Total Debt', 'Long Term Debt And Capital Lease Obligation'),
    )
    equity = _latest(info.balanceSheet, ('Stockholders Equity', 'Total Equity Gross Minority Interest'))
    cash = float(info.totalCash) if info.totalCash is not None else _latest(
        info.balanceSheet,
        ('Cash Cash Equivalents And Short Term Investments', 'Cash And Cash Equivalents'),
    )
    tax_rate = _ratio(tax_provision, pretax_income)
    invested_capital = None
    if total_debt is not None and equity is not None and cash is not None:
        invested_capital = total_debt + equity - cash
    nopat = ebit * (1 - tax_rate) if ebit is not None and tax_rate is not None else None
    return _metric(_ratio(nopat, invested_capital), info)


def roce(info: YFinanceTickerInfo) -> Metric:
    ebit = _latest(info.incomeStatement, ('Operating Income', 'EBIT'))
    assets = _latest(info.balanceSheet, ('Total Assets',))
    current_liabilities = _current_liabilities(info)
    capital_employed = (
        assets - current_liabilities
        if assets is not None and current_liabilities is not None
        else None
    )
    return _metric(_ratio(ebit, capital_employed), info)


def return_on_equity_5y(info: YFinanceTickerInfo) -> Metric:
    return _metric(
        _average_return(
            info,
            ('Net Income Common Stockholders', 'Net Income'),
            ('Stockholders Equity', 'Total Equity Gross Minority Interest'),
            5,
        ),
        info,
    )


def return_on_equity_10y(info: YFinanceTickerInfo) -> Metric:
    return _metric(
        _average_return(
            info,
            ('Net Income Common Stockholders', 'Net Income'),
            ('Stockholders Equity', 'Total Equity Gross Minority Interest'),
            10,
        ),
        info,
    )


def gross_margin(info: YFinanceTickerInfo) -> Metric:
    return _metric(info.grossMargins, info)


def gross_profit(info: YFinanceTickerInfo) -> Metric:
    value = info.grossProfits or _latest(info.incomeStatement, ('Gross Profit',))
    return money_metric(value, info)


def ebitda(info: YFinanceTickerInfo) -> Metric:
    return money_metric(info.ebitda or _latest(info.incomeStatement, ('EBITDA',)), info)


def ebitda_margin(info: YFinanceTickerInfo) -> Metric:
    return _metric(info.ebitdaMargins, info)


def operating_cash_flow(info: YFinanceTickerInfo) -> Metric:
    return money_metric(_cash_flow(info), info)


def capital_expenditures(info: YFinanceTickerInfo) -> Metric:
    return money_metric(_capex(info), info)


def fcf_margin(info: YFinanceTickerInfo) -> Metric:
    return _metric(_ratio(_free_cash_flow(info), info.totalRevenue), info)


def fcf_growth(info: YFinanceTickerInfo) -> Metric:
    return _metric(_cagr(info.cashFlow, ('Free Cash Flow',), 1), info)


def cash_conversion(info: YFinanceTickerInfo) -> Metric:
    net_income = info.netIncomeToCommon or _latest(
        info.incomeStatement,
        ('Net Income Common Stockholders', 'Net Income'),
    )
    return _metric(_ratio(_cash_flow(info), net_income), info)


def operating_cash_flow_margin(info: YFinanceTickerInfo) -> Metric:
    revenue = info.totalRevenue or _latest(info.incomeStatement, ('Total Revenue', 'Operating Revenue'))
    return _metric(_ratio(_cash_flow(info), revenue), info)


def owner_earnings(info: YFinanceTickerInfo) -> Metric:
    return money_metric(_free_cash_flow(info), info)


def owner_earnings_growth(info: YFinanceTickerInfo) -> Metric:
    return _metric(_cagr(info.cashFlow, ('Free Cash Flow',), 1), info)


def owner_earnings_yield(info: YFinanceTickerInfo) -> Metric:
    return _metric(_ratio(_free_cash_flow(info), _market_cap(info)), info)


def net_debt(info: YFinanceTickerInfo) -> Metric:
    debt = float(info.totalDebt) if info.totalDebt is not None else _latest(
        info.balanceSheet,
        ('Total Debt', 'Long Term Debt And Capital Lease Obligation'),
    )
    cash = float(info.totalCash) if info.totalCash is not None else _latest(
        info.balanceSheet,
        ('Cash Cash Equivalents And Short Term Investments', 'Cash And Cash Equivalents'),
    )
    return money_metric(
        debt - cash if debt is not None and cash is not None else None,
        info,
    )


def net_debt_to_ebitda(info: YFinanceTickerInfo) -> Metric:
    ebitda_value = info.ebitda or _latest(info.incomeStatement, ('EBITDA',))
    return _metric(_ratio(_amount(net_debt(info).value), ebitda_value), info)


def revenue_cagr_5y(info: YFinanceTickerInfo) -> Metric:
    return _metric(_cagr(info.incomeStatement, ('Total Revenue', 'Operating Revenue'), 5), info)


def revenue_cagr_10y(info: YFinanceTickerInfo) -> Metric:
    return _metric(_cagr(info.incomeStatement, ('Total Revenue', 'Operating Revenue'), 10), info)


def eps_cagr_5y(info: YFinanceTickerInfo) -> Metric:
    return _metric(_cagr(info.incomeStatement, ('Diluted EPS', 'Basic EPS'), 5), info)


def eps_cagr_10y(info: YFinanceTickerInfo) -> Metric:
    return _metric(_cagr(info.incomeStatement, ('Diluted EPS', 'Basic EPS'), 10), info)


def fcf_cagr_5y(info: YFinanceTickerInfo) -> Metric:
    return _metric(_cagr(info.cashFlow, ('Free Cash Flow',), 5), info)


def fcf_cagr_10y(info: YFinanceTickerInfo) -> Metric:
    return _metric(_cagr(info.cashFlow, ('Free Cash Flow',), 10), info)


def shares_outstanding(info: YFinanceTickerInfo) -> Metric:
    value = info.sharesOutstanding or _latest(
        info.balanceSheet,
        ('Ordinary Shares Number', 'Share Issued'),
    )
    return _metric(value, info)


def shares_outstanding_growth(info: YFinanceTickerInfo) -> Metric:
    return _metric(_cagr(info.balanceSheet, ('Ordinary Shares Number', 'Share Issued'), 1), info)


def buyback_yield(info: YFinanceTickerInfo) -> Metric:
    shares = _series(info.balanceSheet, ('Ordinary Shares Number', 'Share Issued'))
    if len(shares) < 2:
        return _metric(None, info)
    previous = shares[-2][1]
    current = shares[-1][1]
    return _metric((previous - current) / previous if previous else None, info)


def shareholder_yield(info: YFinanceTickerInfo) -> Metric:
    buyback = buyback_yield(info).value
    if not info.dividendHistory or info.currentPrice in (None, 0):
        return _metric(None, info)
    latest_year = info.dividendHistory[-1].date.year
    dividends = sum(
        event.amount
        for event in info.dividendHistory
        if event.date.year == latest_year
    )
    dividend_yield = dividends / info.currentPrice
    return _metric(dividend_yield + buyback if buyback is not None else dividend_yield, info)


def retained_earnings(info: YFinanceTickerInfo) -> Metric:
    return money_metric(_latest(info.balanceSheet, ('Retained Earnings',)), info)


def retained_earnings_growth(info: YFinanceTickerInfo) -> Metric:
    return _metric(_cagr(info.balanceSheet, ('Retained Earnings',), 1), info)


def acquisition_spending(info: YFinanceTickerInfo) -> Metric:
    value = _latest(
        info.cashFlow,
        ('Purchase Of Business', 'Net Business Purchase And Sale', 'Net Investment Purchase And Sale'),
    )
    return money_metric(abs(value) if value is not None else None, info)


def working_capital(info: YFinanceTickerInfo) -> Metric:
    current_assets = _current_assets(info)
    current_liabilities = _current_liabilities(info)
    return money_metric(
        current_assets - current_liabilities
        if current_assets is not None and current_liabilities is not None
        else None,
        info,
    )


def change_in_working_capital(info: YFinanceTickerInfo) -> Metric:
    assets = _series(info.balanceSheet, ('Current Assets', 'Total Current Assets'))
    liabilities = dict(_series(info.balanceSheet, ('Current Liabilities', 'Total Current Liabilities')))
    values = [
        (period, current_assets - liabilities[period])
        for period, current_assets in assets
        if period in liabilities
    ]
    if len(values) < 2:
        return _metric(None, info)
    return money_metric(values[-1][1] - values[-2][1], info)


def receivables(info: YFinanceTickerInfo) -> Metric:
    return money_metric(
        _latest(info.balanceSheet, ('Receivables', 'Accounts Receivable')),
        info,
    )


def inventory(info: YFinanceTickerInfo) -> Metric:
    return money_metric(_latest(info.balanceSheet, ('Inventory',)), info)


def accounts_payable(info: YFinanceTickerInfo) -> Metric:
    return money_metric(_latest(info.balanceSheet, ('Accounts Payable',)), info)


EVALUATOR: MetricEvaluator = NONE_EVALUATOR
