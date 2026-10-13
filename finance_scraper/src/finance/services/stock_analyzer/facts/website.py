# ================================================== #
# MODULE: website
# ================================================== #


from datatypes import YFinanceTickerInfo
from finance.services.stock_analyzer.utils import NONE_EVALUATOR, get_evaluator
from finance.services.stock_analyzer.models import Fact, MetricEvaluator


def extractor(info: YFinanceTickerInfo) -> Fact:
    return Fact(
        fact=info.website
    )

EVALUATOR: MetricEvaluator = NONE_EVALUATOR
