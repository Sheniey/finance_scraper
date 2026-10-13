# ================================================== #
# MODULE: pe_ratio
# ================================================== #


from datatypes import YFinanceTickerInfo
from finance.services.stock_analyzer.utils import get_evaluator, verify_availability
from finance.services.stock_analyzer.models import Metric, MetricEvaluator


def extractor(info: YFinanceTickerInfo) -> Metric:
    if any(x is None for x in (info.currentPrice, info.epsCurrentYear)):
        m: Metric = Metric(metric=None)
        verify_availability(m, info)
        return m
    
    m: Metric = Metric(
        metric=info.currentPrice / info.epsCurrentYear
    )
    verify_availability(m, info)
    return m

EVALUATOR: MetricEvaluator = get_evaluator('valuation.pe_ratio')
