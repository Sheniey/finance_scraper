# ================================================== #
# MODULE: last_dividend
# ================================================== #


from datatypes import YFinanceTickerInfo
from finance.services.stock_analyzer.utils import get_evaluator, money_value
from finance.services.stock_analyzer.models import Fact, MetricEvaluator


def extractor(info: YFinanceTickerInfo) -> Fact:
    return Fact(
        fact=money_value(info.lastDividendValue, info)
    )

EVALUATOR: MetricEvaluator = get_evaluator('fact.last_dividend')
