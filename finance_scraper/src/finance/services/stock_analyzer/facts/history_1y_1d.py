# ================================================== #
# MODULE: history_1y_1d
# ================================================== #

from finance.services.stock_analyzer.models import Fact, MetricEvaluator
from finance.services.stock_analyzer.utils import NONE_EVALUATOR
from datatypes import YFinanceTickerInfo


def extractor(info: YFinanceTickerInfo) -> Fact:
    return Fact(fact=info.history_1y_1d)


EVALUATOR: MetricEvaluator = NONE_EVALUATOR
