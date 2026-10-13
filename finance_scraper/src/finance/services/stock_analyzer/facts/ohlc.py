# ================================================== #
# MODULE: ohlc
# ================================================== #

from finance.services.stock_analyzer.models import Fact, MetricEvaluator
from finance.services.stock_analyzer.utils import money_value, NONE_EVALUATOR
from datatypes import YFinanceTickerInfo


def _value(info: YFinanceTickerInfo, *fields: str) -> float | None:
    for field in fields:
        value = getattr(info, field, None)
        if value is not None:
            return value
    return None


def open_extractor(info: YFinanceTickerInfo) -> Fact:
    return Fact(fact=money_value(_value(info, 'regularMarketOpen', 'open'), info))


def high_extractor(info: YFinanceTickerInfo) -> Fact:
    return Fact(fact=money_value(_value(info, 'regularMarketDayHigh', 'dayHigh', 'high'), info))


def low_extractor(info: YFinanceTickerInfo) -> Fact:
    return Fact(fact=money_value(_value(info, 'regularMarketDayLow', 'dayLow', 'low'), info))


def close_extractor(info: YFinanceTickerInfo) -> Fact:
    return Fact(
        fact=money_value(
            _value(info, 'close', 'currentPrice', 'regularMarketPreviousClose', 'previousClose'),
            info,
        )
    )


EVALUATOR: MetricEvaluator = NONE_EVALUATOR
