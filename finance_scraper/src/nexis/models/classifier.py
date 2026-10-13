
import math
from dataclasses import dataclass, field

from datatypes import Percentage

from nexis.misc.literals import TradingPeriodUnit
from nexis.models.forecast import ForecastResult
from nexis.actions import TradingAction


# ================================================== #
# MODELS                                             #
# ================================================== #

@dataclass(frozen=True)
class TradingSignal:
    action: TradingAction
    probability: Percentage

@dataclass(frozen=True)
class ClassifierMetadata:
    name: str
    signals: tuple[TradingSignal, ...]
    mae: float | None
    rmse: float | None

@dataclass(frozen=True)
class TradingDecision:
    signals: tuple[TradingSignal, ...]
    horizon: int
    horizon_unit: TradingPeriodUnit
    metadata: tuple[ClassifierMetadata, ...] = field(default_factory=tuple)
    forecast: ForecastResult | None = None

    @property
    def top_signal(self) -> TradingSignal:
        return self.signals[0]

    @property
    def probability(self) -> Percentage:
        return self.top_signal.probability

    @property
    def decision_margin(self) -> Percentage:
        if len(self.signals) == 1:
            return Percentage(100.0)

        top_probability: float = float(self.signals[0].probability)
        second_probability: float = float(self.signals[1].probability)
        confidence_margin: float = max(top_probability - second_probability, 0.0)
        return Percentage(confidence_margin)

    @property
    def confidence(self) -> Percentage:
        return Percentage(self.decision_margin.value * 2)

    @property
    def entropy(self) -> Percentage:
        probs: list[float] = [
            float(signal.probability) / 100.0
            for signal in self.signals
        ]

        if len(probs) <= 1:
            return Percentage(0.0)

        entropy: float = -sum(
            p * math.log2(p)
            for p in probs
            if p > 0
        )

        max_entropy: float = math.log2(len(probs))

        return Percentage(entropy / max_entropy * 100)

    @property
    def score(self) -> float:
        margin: float = min(float(self.confidence / 100), 1.0)
        decision_margin: float = float(self.decision_margin / 100)
        certain: float = float((100.0 - self.entropy) / 100.0)

        return (
            0.45 * margin
            +
            0.35 * decision_margin
            +
            0.20 * certain
        )
