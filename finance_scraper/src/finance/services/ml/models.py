
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

from nexis.actions import TradingAction
from nexis.forecaster import ForecastTrend
from datatypes import Percentage


type PeriodUnit = Literal['day']

Actions = TradingAction


class ActionProbability(BaseModel):
    model_config: ConfigDict = ConfigDict(arbitrary_types_allowed=True)

    action: Actions
    probability: Percentage


class ForecastPricePoint(BaseModel):
    model_config: ConfigDict = ConfigDict(arbitrary_types_allowed=True)

    date: date
    predicted: float
    quantiles: dict[str, float]


class ForecastSummary(BaseModel):
    """TimesFM's own view of the future: not a BUY/HOLD/SELL decision, but a
    day-by-day price path (with uncertainty) up to `horizon`. Meant to be
    handed off to whatever component ends up charting it."""

    model_config: ConfigDict = ConfigDict(arbitrary_types_allowed=True)

    ticker: str
    horizon: int
    horizon_unit: PeriodUnit
    trend_signal: ForecastTrend
    expected_return: Percentage
    returns: dict[int, Percentage]
    uncertainty: Percentage
    slope: float
    volatility: Percentage
    prices: list[ForecastPricePoint]


class PredictionResult(BaseModel):
    model_config: ConfigDict = ConfigDict(arbitrary_types_allowed=True)

    ticker: str
    top_action: Actions
    probability: Percentage
    decision_margin: Percentage
    entropy: Percentage
    confidence: Percentage
    score: float
    horizon: int
    horizon_unit: PeriodUnit
    action_probabilities: list[ActionProbability]
    forecast: ForecastSummary | None = Field(default=None)
