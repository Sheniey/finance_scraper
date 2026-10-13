# ================================================== #
# MODULE: ev2market_cap
# ================================================== #


from datatypes import YFinanceTickerInfo
from finance.services.stock_analyzer.utils import get_evaluator, verify_availability
from finance.services.stock_analyzer.models import Metric, MetricEvaluator


def extractor(info: YFinanceTickerInfo) -> Metric:
    if any([
        info.enterpriseValue is None,
        info.marketCap is None
    ]):
        m: Metric = Metric(
            metric=None,
        )
        verify_availability(m, info)
        return m

    m: Metric = Metric(
        metric=info.enterpriseValue / info.marketCap,
    )
    verify_availability(m, info)
    return m

EVALUATOR: MetricEvaluator = get_evaluator('valuation.ev2market_cap')
