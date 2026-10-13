# ================================================== #
# MODULE: dividend_yield
# ================================================== #


from datatypes import YFinanceTickerInfo
from finance.services.stock_analyzer.utils import get_evaluator, verify_availability
from finance.services.stock_analyzer.models import Fact, MetricEvaluator


def extractor(info: YFinanceTickerInfo) -> Fact:
    dividend_yield = info.dividendYield
    if dividend_yield is not None and abs(dividend_yield) > 1:
        dividend_yield /= 100

    return Fact(
        fact=dividend_yield
    )

EVALUATOR: MetricEvaluator = get_evaluator('fact.dividend_yield')
