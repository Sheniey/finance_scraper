# ================================================== #
# MODULE: quote_type
# ================================================== #

from finance.services.stock_analyzer.models import Fact, MetricEvaluator
from finance.services.stock_analyzer.utils import NONE_EVALUATOR
from datatypes import YFinanceTickerInfo


def extractor(info: YFinanceTickerInfo) -> Fact:
    return Fact(fact=info.quoteType)


EVALUATOR: MetricEvaluator = NONE_EVALUATOR
