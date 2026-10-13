# ================================================== #
# MODULE: quick_ratio
# ================================================== #


from datatypes import YFinanceTickerInfo
from finance.services.stock_analyzer.utils import get_evaluator, verify_availability
from finance.services.stock_analyzer.models import Metric, MetricEvaluator


def extractor(info: YFinanceTickerInfo) -> Metric:
    m: Metric = Metric(
        metric=info.quickRatio
    )
    verify_availability(m, info)
    return m

EVALUATOR: MetricEvaluator = get_evaluator('financial_health.quick_ratio')
