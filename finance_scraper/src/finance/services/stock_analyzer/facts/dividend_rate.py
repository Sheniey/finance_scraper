# ================================================== #
# MODULE: dividend_rate
# ================================================== #


from datatypes import YFinanceTickerInfo
from finance.services.stock_analyzer.utils import get_evaluator, money_value
from finance.services.stock_analyzer.models import Fact, MetricEvaluator


def extractor(info: YFinanceTickerInfo) -> Fact:
    return Fact(
        fact=money_value(info.dividendRate, info)
    )

EVALUATOR: MetricEvaluator = get_evaluator('fact.dividend_rate')
