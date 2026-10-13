# ================================================== #
# MODULE: free_cash_flow
# ================================================== #


from datatypes import YFinanceTickerInfo
from finance.services.stock_analyzer.utils import get_evaluator, money_metric
from finance.services.stock_analyzer.models import Metric, MetricEvaluator


def extractor(info: YFinanceTickerInfo) -> Metric:
    return money_metric(info.freeCashflow, info)

EVALUATOR: MetricEvaluator = get_evaluator('financial_health.free_cash_flow')
