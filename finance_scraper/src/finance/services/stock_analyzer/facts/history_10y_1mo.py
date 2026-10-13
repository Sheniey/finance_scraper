# ================================================== #
# MODULE: history_10y_1mo
# ================================================== #


from datatypes import YFinanceTickerInfo
from finance.services.stock_analyzer.utils import NONE_EVALUATOR, get_evaluator
from finance.services.stock_analyzer.models import Fact, MetricEvaluator


def extractor(info: YFinanceTickerInfo) -> Fact:
    return Fact(
        fact=info.history
    )

EVALUATOR: MetricEvaluator = NONE_EVALUATOR

