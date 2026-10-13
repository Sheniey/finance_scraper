# ================================================== #
# MODULE: address
# ================================================== #


from datatypes import YFinanceTickerInfo
from finance.services.stock_analyzer.utils import NONE_EVALUATOR
from finance.services.stock_analyzer.models import Fact, MetricEvaluator


def extractor(info: YFinanceTickerInfo) -> Fact:
    return Fact(
        fact=info.address1
    )

EVALUATOR: MetricEvaluator = NONE_EVALUATOR
