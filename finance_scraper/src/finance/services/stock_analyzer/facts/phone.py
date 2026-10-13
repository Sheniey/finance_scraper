# ================================================== #
# MODULE: phone
# ================================================== #

from finance.services.stock_analyzer.models import Fact, MetricEvaluator
from finance.services.stock_analyzer.utils import NONE_EVALUATOR
from datatypes import YFinanceTickerInfo


def extractor(info: YFinanceTickerInfo) -> Fact:
    return Fact(fact=info.phone)


EVALUATOR: MetricEvaluator = NONE_EVALUATOR
