# ================================================== #
# MODULE: repository
# ================================================== #


import hashlib
import json
from datetime import date
from designkit.behavioral.typing import Assertion

from finance.config import DEFAULT_LANGUAGE
from datatypes import (
    HistoricalMetricPoint,
    YFinanceTickerInfo,
)
from finance.types import Language
from finance.services.report_store.cache import cache
from finance.services.stock_analyzer import extract
from finance.services.stock_analyzer.models import Fact, Metric
from finance.services.stock_analyzer.utils import (
    NONE_EVALUATOR,
    fact_to_metric,
    get_evaluator,
    money_value,
)
from finance.services.stock_analyzer.schema import (
    QuantifiableFacts,
    DescriptiveFacts,
    Valuation,
    Growth,
    Profitability,
    CashFlow,
    FinancialHealth,
    CapitalAllocation,
    History10Y1Mo,
    WorkingCapital,
    StockAnalysis,
)


def _evaluate(
    metric: Metric,
    mnemonic: str,
    language: str | Language | None,
) -> Metric:
    return metric.evaluate(get_evaluator(mnemonic, language))


def _raw(metric: Metric) -> Metric:
    return metric.evaluate(NONE_EVALUATOR)


def _normalize_yield(value: float | None) -> float | None:
    if value is not None and abs(value) > 1:
        return value / 100
    return value


def _statement_series(
    statement: object,
    labels: tuple[str, ...],
) -> list[HistoricalMetricPoint]:
    values = getattr(statement, 'values', {})
    if not isinstance(values, dict):
        return []

    for label in labels:
        direct = values.get(label)

        # El label puede no existir o tener un valor que no sea un diccionario
        if not isinstance(direct, dict):
            continue

        points: list[HistoricalMetricPoint] = []

        for period, value in direct.items():
            if not isinstance(value, (int, float)):
                continue

            try:
                point_date = date.fromisoformat(str(period)[:10])
            except (ValueError, TypeError):
                continue

            points.append(
                HistoricalMetricPoint(
                    date=point_date,
                    value=float(value),
                )
            )

        # Devolvemos la primera serie válida encontrada
        if points:
            return sorted(points, key=lambda point: point.date)

    points: list[HistoricalMetricPoint] = []
    for period, rows in values.items():
        if not isinstance(rows, dict):
            continue
        for label in labels:
            value = rows.get(label)
            if isinstance(value, (int, float)):
                points.append(
                    HistoricalMetricPoint(
                        date=date.fromisoformat(str(period)[:10]),
                        value=float(value),
                    )
                )
                break
    return sorted(points, key=lambda point: point.date)


def _history_facts(payload: YFinanceTickerInfo) -> History10Y1Mo:
    dividends = [
        HistoricalMetricPoint(date=item.date, value=float(item.amount))
        for item in payload.dividendHistory
    ]
    return History10Y1Mo(
        price=extract.history_10y_1mo(payload),
        revenue=Fact(
            fact=_statement_series(
                payload.incomeStatement,
                ('Total Revenue', 'Operating Revenue', 'Revenue'),
            )
        ),
        earnings=Fact(
            fact=_statement_series(
                payload.incomeStatement,
                ('Net Income', 'Net Income Common Stockholders', 'NetIncome'),
            )
        ),
        free_cash_flow=Fact(
            fact=_statement_series(
                payload.cashFlow,
                ('Free Cash Flow', 'FreeCashFlow'),
            )
        ),
        dividends=Fact(fact=dividends),
        sp500=Fact(fact=payload.sp500_history),
    )



def _analysis_cache_identity(
    payload: YFinanceTickerInfo,
    language: str | Language | None,
) -> tuple[str, Language]:
    selected_language: Language = (
        language
        if isinstance(language, Language)
        else Language(**DEFAULT_LANGUAGE)
        if language is None
        else Language(code=language, name=language)
    )
    cache_payload: str = json.dumps(
        {
            'ticker': payload.symbol,
            'region': payload.region,
            'language': selected_language.model_dump(mode='json'),
        },
        ensure_ascii=False,
        separators=(',', ':'),
        sort_keys=True,
    )
    cache_key: str = hashlib.sha256(
        cache_payload.encode('utf-8'),
    ).hexdigest()
    return cache_key, selected_language


def analyze_stock(
    payload: YFinanceTickerInfo,
    language: str | Language | None = None
) -> StockAnalysis:
    Assertion(payload).must_be(YFinanceTickerInfo)

    cache_key, selected_language = _analysis_cache_identity(
        payload,
        language,
    )
    cached_analysis: bytes | None = cache.get('stock_analysis', cache_key)
    if cached_analysis is not None:
        return StockAnalysis.model_validate_json(cached_analysis)

    quantifiable_facts: QuantifiableFacts = QuantifiableFacts(
        price=fact_to_metric(extract.price(payload)).evaluate(
            get_evaluator('fact.price', language),
            Metric(metric=money_value(payload.previousClose, payload)),
        ),
        dividend_yield=fact_to_metric(extract.dividend_yield(payload)).evaluate(
            get_evaluator('fact.dividend_yield', language),
            Metric(metric=_normalize_yield(payload.fiveYearAvgDividendYield)),
        ),
        dividend_rate=fact_to_metric(extract.dividend_rate(payload)).evaluate(
            get_evaluator('fact.dividend_rate', language)
        ),
    )

    descriptive_facts: DescriptiveFacts = DescriptiveFacts(
        ticker=extract.ticker(payload),
        name=extract.name(payload),
        formal_name=extract.formal_name(payload),
        currency=extract.currency(payload),
        region=extract.region(payload),
        address=extract.address(payload),
        industry=extract.industry(payload),
        sector=extract.sector(payload),
        description=extract.description(payload),
        website=extract.website(payload),
        dividends=extract.dividends(payload),
        last_dividend=extract.last_dividend(payload),
        splits=extract.splits(payload),
        history_10y_1mo=extract.history_10y_1mo(payload),
        history_5y_1d=extract.history_5y_1d(payload),
        history_1y_1d=extract.history_1y_1d(payload),
        history_3mo_1d=extract.history_3mo_1d(payload),
        history_1w_1d=extract.history_1w_1d(payload),
        open=extract.open(payload),
        high=extract.high(payload),
        low=extract.low(payload),
        close=extract.close(payload),
        phone=extract.phone(payload),
        quote_type=extract.quote_type(payload),
    )

    valuation: Valuation = Valuation(
        pe_ratio=_evaluate(
            extract.pe_ratio(payload),
            'valuation.pe_ratio',
            language,
        ),
        peg_ratio=_evaluate(
            extract.peg_ratio(payload),
            'valuation.peg_ratio',
            language,
        ),
        trailing_pe_ratio=_evaluate(
            extract.trailing_pe_ratio(payload),
            'valuation.trailing_pe_ratio',
            language,
        ),
        forward_pe_ratio=_evaluate(
            extract.forward_pe_ratio(payload),
            'valuation.forward_pe_ratio',
            language,
        ),
        ev_to_market_cap=_evaluate(
            extract.ev_to_market_cap(payload),
            'valuation.ev2market_cap',
            language,
        ),
        price_to_fcf=_evaluate(
            extract.price_to_fcf(payload),
            'valuation.price_to_fcf',
            language,
        ),
        ev_to_ebitda=_evaluate(
            extract.ev_to_ebitda(payload),
            'valuation.ev_to_ebitda',
            language,
        ),
        ev_to_ebit=_evaluate(
            extract.ev_to_ebit(payload),
            'valuation.ev_to_ebit',
            language,
        ),
        price_to_book=_evaluate(
            extract.price_to_book(payload),
            'valuation.price_to_book',
            language,
        ),
        price_to_sales=_evaluate(
            extract.price_to_sales(payload),
            'valuation.price_to_sales',
            language,
        ),
        earnings_yield=_evaluate(
            extract.earnings_yield(payload),
            'valuation.earnings_yield',
            language,
        ),
    )

    growth: Growth = Growth(
        revenue_growth=_evaluate(
            extract.revenue_growth(payload),
            'growth.revenue_growth',
            language,
        ),
        earnings_growth=_evaluate(
            extract.earnings_growth(payload),
            'growth.earnings_growth',
            language,
        ),
        eps_growth=_evaluate(
            extract.eps_growth(payload),
            'growth.eps_growth',
            language,
        ),
        revenue_cagr_5y=_evaluate(
            extract.revenue_cagr_5y(payload),
            'growth.revenue_cagr_5y',
            language,
        ),
        revenue_cagr_10y=_evaluate(
            extract.revenue_cagr_10y(payload),
            'growth.revenue_cagr_10y',
            language,
        ),
        eps_cagr_5y=_evaluate(
            extract.eps_cagr_5y(payload),
            'growth.eps_cagr_5y',
            language,
        ),
        eps_cagr_10y=_evaluate(
            extract.eps_cagr_10y(payload),
            'growth.eps_cagr_10y',
            language,
        ),
        fcf_cagr_5y=_evaluate(
            extract.fcf_cagr_5y(payload),
            'growth.fcf_cagr_5y',
            language,
        ),
        fcf_cagr_10y=_evaluate(
            extract.fcf_cagr_10y(payload),
            'growth.fcf_cagr_10y',
            language,
        ),
        fcf_growth=_evaluate(
            extract.fcf_growth(payload),
            'growth.fcf_growth',
            language,
        ),
        owner_earnings_growth=_evaluate(
            extract.owner_earnings_growth(payload),
            'growth.owner_earnings_growth',
            language,
        ),
        shares_outstanding_growth=_evaluate(
            extract.shares_outstanding_growth(payload),
            'growth.shares_outstanding_growth',
            language,
        ),
        retained_earnings_growth=_evaluate(
            extract.retained_earnings_growth(payload),
            'growth.retained_earnings_growth',
            language,
        ),
    )

    profitability: Profitability = Profitability(
        profit_margin=_evaluate(
            extract.profit_margin(payload),
            'profitability.profit_margins',
            language,
        ),
        operating_margin=_evaluate(
            extract.operating_margin(payload),
            'profitability.operating_margin',
            language,
        ),
        return_on_equity=_evaluate(
            extract.return_on_equity(payload),
            'profitability.return_on_equity',
            language,
        ),
        return_on_assets=_evaluate(
            extract.return_on_assets(payload),
            'profitability.return_on_assets',
            language,
        ),
        roic=_evaluate(extract.roic(payload), 'profitability.roic', language),
        roce=_evaluate(extract.roce(payload), 'profitability.roce', language),
        return_on_equity_5y=_evaluate(
            extract.return_on_equity_5y(payload),
            'profitability.return_on_equity_5y',
            language,
        ),
        return_on_equity_10y=_evaluate(
            extract.return_on_equity_10y(payload),
            'profitability.return_on_equity_10y',
            language,
        ),
        gross_margin=_evaluate(
            extract.gross_margin(payload),
            'profitability.gross_margin',
            language,
        ),
        gross_profit=_raw(extract.gross_profit(payload)),
        ebitda=_raw(extract.ebitda(payload)),
        ebitda_margin=_evaluate(
            extract.ebitda_margin(payload),
            'profitability.ebitda_margin',
            language,
        ),
    )

    cash_flow: CashFlow = CashFlow(
        operating_cash_flow=_raw(extract.operating_cash_flow(payload)),
        capital_expenditures=_raw(extract.capital_expenditures(payload)),
        fcf_margin=_evaluate(
            extract.fcf_margin(payload),
            'cash_flow.fcf_margin',
            language,
        ),
        cash_conversion=_evaluate(
            extract.cash_conversion(payload),
            'cash_flow.cash_conversion',
            language,
        ),
        operating_cash_flow_margin=_evaluate(
            extract.operating_cash_flow_margin(payload),
            'cash_flow.operating_cash_flow_margin',
            language,
        ),
        owner_earnings=_raw(extract.owner_earnings(payload)),
        owner_earnings_yield=_evaluate(
            extract.owner_earnings_yield(payload),
            'cash_flow.owner_earnings_yield',
            language,
        ),
    )

    financial_health = FinancialHealth(
        debt_to_equity=_evaluate(
            extract.debt_to_equity(payload),
            'financial_health.debt_to_equity',
            language,
        ),
        current_ratio=_evaluate(
            extract.current_ratio(payload),
            'financial_health.current_ratio',
            language,
        ),
        quick_ratio=_evaluate(
            extract.quick_ratio(payload),
            'financial_health.quick_ratio',
            language,
        ),
        free_cash_flow=_raw(extract.free_cash_flow(payload)),
        net_debt=_raw(extract.net_debt(payload)),
        net_debt_to_ebitda=_evaluate(
            extract.net_debt_to_ebitda(payload),
            'financial_health.net_debt_to_ebitda',
            language,
        ),
    )

    capital_allocation = CapitalAllocation(
        shares_outstanding=_raw(extract.shares_outstanding(payload)),
        buyback_yield=_evaluate(
            extract.buyback_yield(payload),
            'capital_allocation.buyback_yield',
            language,
        ),
        shareholder_yield=_evaluate(
            extract.shareholder_yield(payload),
            'capital_allocation.shareholder_yield',
            language,
        ),
        retained_earnings=_raw(extract.retained_earnings(payload)),
        acquisition_spending=_raw(extract.acquisition_spending(payload)),
    )

    working_capital = WorkingCapital(
        working_capital=_raw(extract.working_capital(payload)),
        change_in_working_capital=_raw(extract.change_in_working_capital(payload)),
        receivables=_raw(extract.receivables(payload)),
        inventory=_raw(extract.inventory(payload)),
        accounts_payable=_raw(extract.accounts_payable(payload)),
    )

 
    analysis: StockAnalysis = StockAnalysis(
        quantifiable_facts=quantifiable_facts,
        descriptive_facts=descriptive_facts,
        valuation=valuation,
        growth=growth,
        profitability=profitability,
        cash_flow=cash_flow,
        financial_health=financial_health,
        capital_allocation=capital_allocation,
        working_capital=working_capital,
        history_10y_1mo=_history_facts(payload),
    )
    cache.set(
        'stock_analysis',
        cache_key,
        analysis.model_dump_json().encode('utf-8'),
        ttl_seconds=3600,
        metadata={
            'ticker': analysis.descriptive_facts.ticker,
            'language': selected_language.code,
            'style': selected_language.style,
        },
    )
    return analysis
