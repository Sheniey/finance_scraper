# ================================================== #
# MODULE: dividends
# ================================================== #


from datatypes import YFinanceTickerInfo
from finance.services.stock_analyzer.utils import NONE_EVALUATOR
from finance.services.stock_analyzer.models import Fact, MetricEvaluator


def extractor(info: YFinanceTickerInfo) -> Fact:
    if not info.dividendHistory:
        return Fact(
            fact='Cannot find historical dividend information for this ticker.'
        )

    latest = info.dividendHistory[-1]
    return Fact(
        fact=f'{len(info.dividendHistory)} payments; latest {latest.amount:.4f} on {latest.date.isoformat()}'
    )

EVALUATOR: MetricEvaluator = NONE_EVALUATOR
