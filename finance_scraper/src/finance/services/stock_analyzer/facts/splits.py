# ================================================== #
# MODULE: splits
# ================================================== #


from datatypes import YFinanceTickerInfo
from finance.services.stock_analyzer.utils import NONE_EVALUATOR
from finance.services.stock_analyzer.models import Fact, MetricEvaluator


def extractor(info: YFinanceTickerInfo) -> Fact:
    if not info.splitHistory:
        return Fact()

    latest = info.splitHistory[-1]
    return Fact(fact=f'{latest.ratio} on {latest.date.isoformat()}')

EVALUATOR: MetricEvaluator = NONE_EVALUATOR
