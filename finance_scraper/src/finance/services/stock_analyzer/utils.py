# ================================================== #
# MODULE: utils
# ================================================== #


from datatypes import Currency
from designkit.behavioral.typing import Assertion

from finance.services.stock_analyzer.definitions.definition import load_definitions
from finance.config import DEFAULT_LANGUAGE, lru_cache
from finance.services.i18n import i18n
from finance.services.i18n.models import I18nSnapshot
from finance.types.language import Language
from finance.services.stock_analyzer.definitions import (
    defs, DefinitionEntry,
    args, DefEntryArguments
)
from finance.services.stock_analyzer.models import (
    Fact, Metric,
    MetricEvaluator,
    MetricGrade,
    MetricStatus,
    MetricRule
)
from datatypes import Money, YFinanceTickerInfo


def fact_to_metric(fact: Fact) -> Metric:
    return Metric(
        metric=fact.value
    )

def metric_to_fact(metric: Metric) -> Fact:
    return Fact(
        fact=metric.value
    )


def money_value(
    value: int | float | str | Money | None,
    info: YFinanceTickerInfo,
) -> Money | None:
    if value is None:
        return None
    currency_code: str = (
        info.financialCurrency
        or info.currency
        or 'USD'
    )
    currency: Currency | None = Currency.get_by_code(currency_code)
    if currency is None:
        raise ValueError(f'Unknown currency code: {currency_code!r}')
    print(f'Money value: {value}, Currency code: {currency_code}')
    return Money(value, currency)


def money_metric(
    value: int | float | str | Money | None,
    info: YFinanceTickerInfo,
) -> Metric:
    metric: Metric = Metric(metric=money_value(value, info))
    verify_availability(metric, info)
    return metric

def verify_availability(metric: Metric, info: YFinanceTickerInfo) -> None:
    Assertion(metric).must_be(Metric)

    metric.unavailable = (
        True
        if info.quoteType in ['ETF', 'MUTUALFUND']
        and metric.value is None
        else False
    )
    if metric.unavailable:
        metric.status = MetricStatus.NOT_AVAILABLE
    elif metric.value is None and metric.status != MetricStatus.NaN:
        metric.status = MetricStatus.NA

def get_evaluator(
    mnemonic: str,
    language: str | Language | None = None,
) -> MetricEvaluator:
    selected_language: Language = (
        language
        if isinstance(language, Language)
        else Language(**DEFAULT_LANGUAGE) if language is None
        else Language(code=language, name=language)
    )
    return _get_evaluator_cached(
        mnemonic,
        selected_language.code,
        selected_language.name,
        selected_language.style,
    )


@lru_cache()
def _get_evaluator_cached(
    mnemonic: str,
    language_code: str,
    language_name: str,
    language_style: str,
) -> MetricEvaluator:
    load_definitions()
    selected_language = Language(
        code=language_code,
        name=language_name,
        style=language_style,
    )
    t: I18nSnapshot = i18n(
        f'analyzer.{mnemonic}',
        selected_language,
        throw_error=False,
    )
    d: DefinitionEntry = defs(mnemonic)
    a: DefEntryArguments = args(mnemonic)
    snapshot = t('.')
    
    return MetricEvaluator(
        rating_rules=[
            MetricRule(
                threshold=d.rating.definition[MetricGrade.EXCELLENT.value],
                grade=MetricGrade.EXCELLENT,
                feedback=snapshot.rating_thresholds[MetricGrade.EXCELLENT.value],
                threshold_kind=d.rating.arguments.type,
            ),
            MetricRule(
                threshold=d.rating.definition[MetricGrade.VERY_GOOD.value],
                grade=MetricGrade.VERY_GOOD,
                feedback=snapshot.rating_thresholds[MetricGrade.VERY_GOOD.value],
                threshold_kind=d.rating.arguments.type,
            ),
            MetricRule(
                threshold=d.rating.definition[MetricGrade.GOOD.value],
                grade=MetricGrade.GOOD,
                feedback=snapshot.rating_thresholds[MetricGrade.GOOD.value],
                threshold_kind=d.rating.arguments.type,
            ),
            MetricRule(
                threshold=d.rating.definition[MetricGrade.MEH.value],
                grade=MetricGrade.MEH,
                feedback=snapshot.rating_thresholds[MetricGrade.MEH.value],
                threshold_kind=d.rating.arguments.type,
            ),
            MetricRule(
                threshold=d.rating.definition[MetricGrade.BAD.value],
                grade=MetricGrade.BAD,
                feedback=snapshot.rating_thresholds[MetricGrade.BAD.value],
                threshold_kind=d.rating.arguments.type,
            ),
            MetricRule(
                threshold=d.rating.definition[MetricGrade.VERY_BAD.value],
                grade=MetricGrade.VERY_BAD,
                feedback=snapshot.rating_thresholds[MetricGrade.VERY_BAD.value],
                threshold_kind=d.rating.arguments.type,
            ),
            MetricRule(
                threshold=d.rating.definition[MetricGrade.AWFUL.value],
                grade=MetricGrade.AWFUL,
                feedback=snapshot.rating_thresholds[MetricGrade.AWFUL.value],
                threshold_kind=d.rating.arguments.type,
            )
        ] if d.rating.definition else [],
        comparison_rules=[
            MetricRule(
                threshold=d.comparison.definition[MetricGrade.EXCELLENT.value],
                grade=MetricGrade.EXCELLENT,
                feedback=snapshot.comparison_thresholds[MetricGrade.EXCELLENT.value],
                threshold_kind=d.comparison.arguments.type,
            ),
            MetricRule(
                threshold=d.comparison.definition[MetricGrade.VERY_GOOD.value],
                grade=MetricGrade.VERY_GOOD,
                feedback=snapshot.comparison_thresholds[MetricGrade.VERY_GOOD.value],
                threshold_kind=d.comparison.arguments.type,
            ),
            MetricRule(
                threshold=d.comparison.definition[MetricGrade.GOOD.value],
                grade=MetricGrade.GOOD,
                feedback=snapshot.comparison_thresholds[MetricGrade.GOOD.value],
                threshold_kind=d.comparison.arguments.type,
            ),
            MetricRule(
                threshold=d.comparison.definition[MetricGrade.MEH.value],
                grade=MetricGrade.MEH,
                feedback=snapshot.comparison_thresholds[MetricGrade.MEH.value],
                threshold_kind=d.comparison.arguments.type,
            ),
            MetricRule(
                threshold=d.comparison.definition[MetricGrade.BAD.value],
                grade=MetricGrade.BAD,
                feedback=snapshot.comparison_thresholds[MetricGrade.BAD.value],
                threshold_kind=d.comparison.arguments.type,
            ),
            MetricRule(
                threshold=d.comparison.definition[MetricGrade.VERY_BAD.value],
                grade=MetricGrade.VERY_BAD,
                feedback=snapshot.comparison_thresholds[MetricGrade.VERY_BAD.value],
                threshold_kind=d.comparison.arguments.type,
            ),
            MetricRule(
                threshold=d.comparison.definition[MetricGrade.AWFUL.value],
                grade=MetricGrade.AWFUL,
                feedback=snapshot.comparison_thresholds[MetricGrade.AWFUL.value],
                threshold_kind=d.comparison.arguments.type,
            )
        ] if d.comparison.definition else [],
        excellent_is_lowest=a.excellent_is_lowest
    )

NONE_EVALUATOR: MetricEvaluator = MetricEvaluator(
    rating_rules=[],
    comparison_rules=[],
    excellent_is_lowest=False
)
