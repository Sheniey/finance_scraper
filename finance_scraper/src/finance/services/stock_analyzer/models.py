
import math
from typing import Any, Literal, Protocol, Self, TypedDict
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    field_serializer,
    field_validator,
    model_validator,
)
from decimal import Decimal
from enum import Enum, StrEnum

from datatypes import (
    HistoricalMetricPoint,
    Money,
    Percentage,
    YFinanceHistoryPoint,
    YFinanceTickerInfo,
)
from finance.services.stock_analyzer.exceptions import (
    CurrencyMismatchError,
    InvalidMetricThresholdError,
    InvalidRatingRuleError,
    MissingMetricValueError,
)

type Label = str
type Delta = float
type DeltaPct = Percentage
type MetricValue = float | Decimal | Money | None
type FactValue = (
    str
    | int
    | float
    | Decimal
    | Money
    | list[HistoricalMetricPoint]
    | list[YFinanceHistoryPoint]
    | None
)

type MetricRated = tuple[MetricGrade, Label | None]
type MetricCompared = tuple[MetricGrade, Delta | None, DeltaPct | None]
class MetricEvaluated(TypedDict):
    rating: MetricGrade
    comparison: MetricCompared | None



class AnalysisItem(BaseModel):
    @property
    def value(self) -> Any:
        raise NotImplemented

    @property
    def state(self) -> State:
        if self.value is None:
            return State.NA

        return State.OK

    @property
    def is_miss(self) -> bool:
        return self.state == State.NA

class State(StrEnum):
    OK = 'ok'
    NA = 'n/a'



class MetricGrade(StrEnum):
    EXCELLENT = 'excellent'
    VERY_GOOD = 'very_good'
    GOOD = 'good'
    MEH = 'meh'
    BAD = 'bad'
    VERY_BAD = 'very_bad'
    AWFUL = 'awful'

    NA = 'n/a'
    NaN = 'nan'

    def weights() -> dict[MetricGrade, int]:
        return {
            MetricGrade.EXCELLENT: 7,
            MetricGrade.VERY_GOOD: 6,
            MetricGrade.GOOD: 5,
            MetricGrade.MEH: 4,
            MetricGrade.BAD: 3,
            MetricGrade.VERY_BAD: 2,
            MetricGrade.AWFUL: 1,

            MetricGrade.NA: 0,
            MetricGrade.NaN: 0
        }


class MetricStatus(Enum):
    OK = 'OK'
    NA = 'NA'
    NaN = 'NaN'
    NOT_AVAILABLE = 'NOT_AVAILABLE'
    NOT_RATED = 'NOT_RATED'


class MetricRule(BaseModel):
    model_config: ConfigDict = ConfigDict(
        arbitrary_types_allowed=True
    )

    threshold: StrictFloat | Percentage = Field(union_mode='left_to_right')
    grade: MetricGrade
    feedback: Label | None = Field(default=None)
    threshold_kind: Literal['numeric', 'percentage', 'none'] = 'numeric'

    def is_percentage(self) -> bool:
        return self.threshold_kind == 'percentage'
    
    def is_numeric(self) -> bool:
        return self.threshold_kind == 'numeric'
    
    @property
    def weight(self) -> int:
        weights = MetricGrade.weights()
        return weights.get(self.grade, 0)

class MetricEvaluator(BaseModel):
    rating_rules: list[MetricRule]
    comparison_rules: list[MetricRule]
    excellent_is_lowest: bool = False

    def __call__(self, metric: Metric, baseline: Metric | None = None) -> MetricEvaluated:
        return self.evaluate(metric, baseline)

    def evaluate(self, metric: Metric, baseline: Metric | None = None) -> MetricEvaluated:
        rating = self.rate(metric)
        comparison = (
            self.compare(baseline, metric)
            if baseline
            else (MetricGrade.NA, None, None)
        )
        return { 'rating': rating, 'comparison': comparison }

    @staticmethod
    def _validate_best_rule(
        excellent_is_lowest: bool,
        threshold: float | Percentage,
        metric_value: float | Decimal | Money | Percentage,
    ) -> bool:
        if isinstance(metric_value, Money):
            metric_value = float(metric_value.value)

        if isinstance(metric_value, Percentage):
            if not isinstance(threshold, (int, float, Decimal, Percentage)):
                raise InvalidMetricThresholdError(threshold, metric_value)
            return (
                metric_value <= threshold
                if excellent_is_lowest
                else metric_value >= threshold
            )

        if isinstance(metric_value, (int, float, Decimal)) and isinstance(
            threshold,
            (int, float, Decimal),
        ):
            return (
                metric_value <= threshold
                if excellent_is_lowest
                else metric_value >= threshold
            )

        raise InvalidMetricThresholdError(threshold, metric_value)

    @staticmethod
    def _numeric_value(value: MetricValue) -> float:
        if isinstance(value, Money):
            return float(value.value)
        if isinstance(value, (int, float)):
            return float(value)
        raise MissingMetricValueError(value)

    def _matches_comparison_rule(
            self,
            rule: MetricRule,
            delta: float,
            delta_pct: Percentage | None,
        ) -> bool:

        if rule.is_numeric():
            return self._validate_best_rule(
                self.excellent_is_lowest,
                rule.threshold,
                delta,
            )

        if rule.is_percentage() and delta_pct is not None:
            return self._validate_best_rule(
                self.excellent_is_lowest,
                rule.threshold,
                delta_pct,
            )

        return False

    @staticmethod
    def _validate_money_currency(
        previous: MetricValue,
        current: MetricValue,
    ) -> None:
        if (
            isinstance(current, Money)
            and isinstance(previous, Money)
            and not current.verify_currency(previous)
        ):
            raise CurrencyMismatchError(
                str(previous.currency.code),
                str(current.currency.code),
            )

    def _matching_comparison_rules(
        self,
        delta: float,
        delta_pct: Percentage | None,
    ) -> list[MetricRule]:
        return [
            rule
            for rule in self.comparison_rules
            if self._matches_comparison_rule(rule, delta, delta_pct)
        ]

    def rate(self, metric: Metric) -> MetricRated:
        if metric.is_nan:
            return MetricGrade.NaN, 'NaN'

        if metric.is_miss:
            return MetricGrade.NA, 'N/A'

        for rule in self.rating_rules:
            if not rule.is_numeric():
                raise InvalidRatingRuleError(rule.threshold)

            if self._validate_best_rule(self.excellent_is_lowest, rule.threshold, metric.value):
                return rule.grade, rule.feedback

        return MetricGrade.NA, 'N/A'
    
    def compare(self, previous: Metric, current: Metric) -> MetricCompared:
        if current.is_nan or previous.is_nan:
            return MetricGrade.NaN, None, None

        if current.is_miss or previous.is_miss:
            return MetricGrade.NA, None, None

        self._validate_money_currency(previous.value, current.value)

        previous_value = self._numeric_value(previous.value)
        current_value = self._numeric_value(current.value)
        delta: float = current_value - previous_value
        delta_pct: float | None = (
            Percentage.from_fraction(delta / previous_value)
            if previous_value != 0
            else None
        )

        possible_ratings = self._matching_comparison_rules(delta, delta_pct)
        if not possible_ratings:
            return MetricGrade.NA, delta, delta_pct

        possible_ratings.sort(key=lambda r: r.weight, reverse=True)
        best_rule: MetricRule = possible_ratings[0]

        return best_rule.grade, delta, delta_pct

class MetricExtractor(Protocol):
    def __call__(self, info: YFinanceTickerInfo) -> Metric:
        ...

class Metric(AnalysisItem):
    metric: MetricValue = Field(default=None)
    status: MetricStatus = Field(default=MetricStatus.NOT_RATED)
    
    rating: MetricRated | None = Field(default=None, exclude=True)
    comparison: MetricCompared | None = Field(default=None, exclude=True)
    unavailable: bool = Field(default=False, exclude=True)

    @field_validator('metric', mode='before')
    @classmethod
    def normalize_nan(cls, value: Any) -> Any:
        if isinstance(value, float) and math.isnan(value):
            return None
        return value

    @model_validator(mode='before')
    @classmethod
    def preserve_nan_status(cls, value: Any) -> Any:
        if isinstance(value, dict):
            metric = value.get('metric')
            if isinstance(metric, float) and math.isnan(metric):
                value = value.copy()
                value['status'] = MetricStatus.NaN
        return value

    @model_validator(mode='after')
    def normalize_legacy_status(self) -> Self:
        if self.status != MetricStatus.NOT_RATED:
            return self
        if self.unavailable:
            self.status = MetricStatus.NOT_AVAILABLE
            return self
        if self.value is None:
            self.status = MetricStatus.NA
            return self
        if self.rating and self.rating[0] not in (MetricGrade.NA, MetricGrade.NaN):
            self.status = MetricStatus.OK
        return self

    def __str__(self) -> str:
        return str(self.metric) if self.metric is not None else 'N/A'

    @property
    def grade(self) -> MetricGrade | None:
        return (
            self.rating[0]
            if self.rating else

            self.comparison[0]
            if self.comparison else
        
            None
        )

    @property
    def label(self) -> Label | None:
        return self.rating[1] if self.rating else None

    @property
    def delta(self) -> Delta | None:
        return self.comparison[1] if self.comparison else None

    @property
    def delta_pct(self) -> DeltaPct | None:
        return self.comparison[2] if self.comparison else None

    @property
    def is_nan(self) -> bool:
        return (
            self.status == MetricStatus.NaN
            or (
                self.value is not None
            and isinstance(self.value, float)
            and math.isnan(self.value)
            )
        )

    @property
    def value(self) -> MetricValue:
        return self.metric

    def evaluate(self, evaluator: MetricEvaluator, compare_previous: Metric | None = None) -> Self:
        evaluation: MetricEvaluated = evaluator(self, compare_previous)

        self.rating: MetricRated = evaluation['rating']
        self.comparison: MetricCompared = evaluation['comparison']
        self.status = self._evaluated_status()
        return self

    def _evaluated_status(self) -> MetricStatus:
        if self.status == MetricStatus.NaN or self.is_nan:
            return MetricStatus.NaN
        if self.status == MetricStatus.NOT_AVAILABLE:
            return MetricStatus.NOT_AVAILABLE
        if self.unavailable:
            return MetricStatus.NOT_AVAILABLE
        if self.value is None:
            return MetricStatus.NA
        rating = self.rating[0] if self.rating else MetricGrade.NA
        if rating in (MetricGrade.NA, MetricGrade.NaN):
            return MetricStatus.NOT_RATED
        return MetricStatus.OK

class FactExtractor(Protocol):
    def __call__(self, info: YFinanceTickerInfo) -> Fact:
        ...

class Fact(AnalysisItem):
    fact: FactValue | None = Field(default=None)
    unavailable: bool = Field(default=False, exclude=True)
    
    @field_validator('fact', mode='before')
    @classmethod
    def normalize_nan(cls, value: Any) -> Any:
        if isinstance(value, float) and math.isnan(value):
            return None
        return value

    def __str__(self) -> str:
        return str(self.fact) if self.fact is not None else 'N/A'

    @field_serializer('fact')
    def serialize_fact(self, value: FactValue | None) -> Any:
        if isinstance(value, Money):
            return str(value)
        if isinstance(value, list):
            return [
                item.model_dump() if isinstance(item, BaseModel) else item
                for item in value
            ]
        return value

    @property
    def value(self) -> FactValue | None:
        return self.fact
