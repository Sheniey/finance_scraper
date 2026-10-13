
import math, json
from designkit.behavioral.typing import Assertion
from datetime import date, datetime
from typing import Any
from concurrent.futures import Future, ThreadPoolExecutor

from datatypes import (
    Ticker,
    YFinanceDividend,
    YFinanceHistoryPoint,
    YFinanceSplit,
    YFinanceStatement,
    YFinanceTickerInfo,
    YFinanceTicker,
)
from finance.config import Theme
from finance.services.report_store.cache import cache


# ================================================== #
# HELPER FUNCTIONS                                   #
# ================================================== #

def get_data(ticker: Ticker) -> YFinanceTicker:
    return ticker.extract_data()


def _scalar(value: Any) -> int | float | str | None:
    if value is None:
        return None
    
    if hasattr(value, 'item'):
        value = value.item()

    match value:
        case float() if math.isnan(value):
            return None
        
        case datetime() | date():
            return value.isoformat()

        case int() | float() | str():
            return value

        case bool():
            return int(value) 

    return str(value)


def _as_date(value: Any) -> date:
    if Assertion(value).should_have('to_pydatetime'):
        value = value.to_pydatetime()

    match value:
        case datetime():
            return value.date()

        case date():
            return value

    return date.fromisoformat(str(value)[:10])

# that annoying guy from Complexipy wants a helper function, so I'm doing what he requested
def _stmt_point(index: Any, row: Any) -> tuple[str, dict[str, int | float | None]]:
    row_values: dict[str, int | float | None] = {}
    for period, value in row.items():
        normalized: int | float | str | None = _scalar(value)
        assertion: Assertion = Assertion(normalized)

        if assertion.should_be(int, float, None):
            row_values[str(period)[:10]] = normalized

    return str(index), row_values

def _statement(frame: Any) -> YFinanceStatement:
    if frame is None or getattr(frame, 'empty', True):
        return YFinanceStatement()

    values: dict[str, dict[str, int | float | None]] = {}
    for index, row in frame.iterrows():
        period, row_values = _stmt_point(index, row)
        values[period] = row_values

    return YFinanceStatement(values=values)

# that annoying guy from Complexipy wants a helper function, so I'm doing what he requested
def _history_point(index: Any, row: Any) -> YFinanceHistoryPoint:
    open_value: int | float | None = _scalar(row.get('Open'))
    high: int | float | None = _scalar(row.get('High'))
    low: int | float | None = _scalar(row.get('Low'))
    close: int | float | None = _scalar(row.get('Close'))
    adjusted_close: int | float | None = _scalar(row.get('Adj Close'))
    volume: int | float | None = _scalar(row.get('Volume'))

    return YFinanceHistoryPoint(
        date=_as_date(index),
        open=float(open_value) if isinstance(open_value, (int, float)) else None,
        high=float(high) if isinstance(high, (int, float)) else None,
        low=float(low) if isinstance(low, (int, float)) else None,
        close=float(close) if isinstance(close, (int, float)) else None,
        adjusted_close=float(adjusted_close) if isinstance(adjusted_close, (int, float)) else None,
        volume=int(volume) if isinstance(volume, (int, float)) else None,
    )

def _history(frame: Any) -> list[YFinanceHistoryPoint]:
    if frame is None or getattr(frame, 'empty', True):
        return []

    return [
        _history_point(index, row)
        for index, row in frame.iterrows()
    ]

# that annoying guy from Complexipy wants a helper function, so I'm doing what he requested
def _action_point(index: Any, row: Any) -> tuple[YFinanceDividend | None, YFinanceSplit | None]:
    dividend: int | float | None = _scalar(row.get('Dividends'))
    split: int | float | str | None = _scalar(row.get('Stock Splits'))

    dividend_obj: YFinanceDividend | None = None
    split_obj: YFinanceSplit | None = None

    if isinstance(dividend, (int, float)) and Assertion(dividend).should_comply(lambda x: x != 0):
        dividend_obj = YFinanceDividend(date=_as_date(index), amount=float(dividend))

    if Assertion(split).should_be(int, float, str) and split not in (0, '0', ''):
        split_obj = YFinanceSplit(date=_as_date(index), ratio=split)

    return dividend_obj, split_obj

def _actions(frame: Any) -> tuple[list[YFinanceDividend], list[YFinanceSplit]]:
    if frame is None or getattr(frame, 'empty', True):
        return [], []

    dividends: list[YFinanceDividend] = []
    splits: list[YFinanceSplit] = []

    for index, row in frame.iterrows():
        dividend, split = _action_point(index, row)
        if dividend is not None:
            dividends.append(dividend)
        if split is not None:
            splits.append(split)

    return dividends, splits

def _load_info(ticker: YFinanceTicker) -> dict[str, Any]:
    return dict(ticker.info)


def _load_history_points(
    ticker: YFinanceTicker,
    period: str,
    interval: str,
) -> list[YFinanceHistoryPoint]:
    return _history(ticker.history(period=period, interval=interval, auto_adjust=False))


def _load_sp500_history() -> list[YFinanceHistoryPoint]:
    benchmark = YFinanceTicker(Theme.SP500_SYMBOL)
    return _load_history_points(benchmark, '10y', '1mo')


def _load_action_history(ticker: YFinanceTicker) -> tuple[list[YFinanceDividend], list[YFinanceSplit]]:
    return _actions(ticker.actions)


def _load_income_statement(ticker: YFinanceTicker) -> YFinanceStatement:
    return _statement(ticker.financials)


def _load_balance_sheet(ticker: YFinanceTicker) -> YFinanceStatement:
    return _statement(ticker.balance_sheet)


def _load_cash_flow(ticker: YFinanceTicker) -> YFinanceStatement:
    return _statement(ticker.cashflow)


# ================================================== #
# PUBLIC FUNCTIONS                                   #
# ================================================== #

def build_info(ticker: YFinanceTicker) -> YFinanceTickerInfo:
    cache_key: str = ticker.ticker.casefold()
    cached_info: bytes | None = cache.get('yf_info', cache_key)
    if cached_info is not None:
        if isinstance(cached_info, (str, bytes)):
            cached_info = json.loads(cached_info)
        return YFinanceTickerInfo.model_validate(cached_info)

    with ThreadPoolExecutor(max_workers=6) as executor:
        info_future: Future = executor.submit(_load_info, ticker)
        history_future: Future = executor.submit(
            _load_history_points,
            ticker,
            '10y',
            '1mo',
        )
        history_5y_1d_future: Future = executor.submit(
            _load_history_points,
            ticker,
            '5y',
            '1d',
        )
        history_1y_1d_future: Future = executor.submit(
            _load_history_points,
            ticker,
            '1y',
            '1d',
        )
        history_3mo_1d_future: Future = executor.submit(
            _load_history_points,
            ticker,
            '3mo',
            '1d',
        )
        history_1w_1d_future: Future = executor.submit(
            _load_history_points,
            ticker,
            '1wk',
            '1d',
        )
        sp500_history_future: Future | None = (
            executor.submit(_load_sp500_history)
            if isinstance(ticker, YFinanceTicker)
            else None
        )
        actions_future: Future = executor.submit(_load_action_history, ticker)
        income_statement_future: Future = executor.submit(_load_income_statement, ticker)
        balance_sheet_future: Future = executor.submit(_load_balance_sheet, ticker)
        cash_flow_future: Future = executor.submit(_load_cash_flow, ticker)

        info: dict[str, Any] = info_future.result()
        dividends, splits = actions_future.result()

    info.update(
        {
            'history': history_future.result(),
            'history_5y_1d': history_5y_1d_future.result(),
            'history_1y_1d': history_1y_1d_future.result(),
            'history_3mo_1d': history_3mo_1d_future.result(),
            'history_1w_1d': history_1w_1d_future.result(),
            'sp500_history': (
                sp500_history_future.result()
                if sp500_history_future is not None
                else []
            ),
            'dividendHistory': dividends,
            'splitHistory': splits,
            'incomeStatement': income_statement_future.result(),
            'balanceSheet': balance_sheet_future.result(),
            'cashFlow': cash_flow_future.result(),
        }
    )
    result = YFinanceTickerInfo.model_validate(info)
    cache.set(
        'yf_info',
        cache_key,
        json.dumps(
            result.model_dump(mode='json'),
            ensure_ascii=False,
            separators=(',', ':'),
            sort_keys=True,
        ).encode('utf-8'),
        ttl_seconds=900,
        metadata={'ticker': ticker.ticker},
    )
    return result


def get_info(ticker: Ticker) -> YFinanceTickerInfo:
    return build_info(ticker.extract_data())

def create_ticker(symbol: str, region: str) -> Ticker:
    return Ticker(ticker=f'{symbol.upper()}.{region.upper()}')
