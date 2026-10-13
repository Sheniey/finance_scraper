
from typing import Any
from decimal import Decimal
from pandas import Series

from datatypes import Percentage, Ticker

from nexis.config import MODEL_PATH
from nexis.classifier import (
    ActionClassifier,
    TradingAction,
    TradingDecision
)
from nexis.dataset import build_live_features, build_price_history
from nexis.errors import ModelException as MLPipelineException
from nexis.forecaster import ForecastResult
from nexis.predictor import load_forecaster, load_model
from finance.services.ml.models import (
    ActionProbability,
    Actions,
    ForecastPricePoint,
    ForecastSummary,
    PredictionResult
)


def _to_action(action: TradingAction) -> Actions:
    return Actions(action.value)


def _to_percentage(fraction: float) -> Percentage:
    """`Percentage.from_fraction` expects a `Decimal`, not a raw `float`."""
    return Percentage.from_fraction(Decimal(str(fraction)))


def _build_forecast_summary(ticker: Ticker, horizon: int) -> ForecastSummary | None:
    """
    Builds TimesFM's forecast summary for `ticker`. Degrades gracefully
    to `None` (instead of failing the whole prediction) when the forecasting
    model is unavailable or the forecast cannot be generated, since this is
    an additional, optional signal alongside the classifier's decision.
    """

    forecast: ForecastResult
    try:
        history: Series[float] = build_price_history(ticker=ticker)
        forecast = load_forecaster().forecast(ticker, history, horizon=horizon)
    except MLPipelineException:
        return None

    return ForecastSummary(
        ticker=forecast.ticker,
        horizon=forecast.horizon,
        horizon_unit=forecast.horizon_unit,
        trend_signal=forecast.trend_signal,
        expected_return=_to_percentage(forecast.expected_return),
        returns={
            checkpoint: _to_percentage(value)
            for checkpoint, value in forecast.returns.items()
        },
        uncertainty=_to_percentage(forecast.uncertainty),
        slope=forecast.slope,
        volatility=_to_percentage(forecast.volatility),
        prices=[
            ForecastPricePoint(
                date=date,
                predicted=predicted,
                quantiles={
                    quantile_name: values[index]
                    for quantile_name, values in forecast.quantiles.items()
                },
            )
            for index, (date, predicted) in enumerate(zip(forecast.dates, forecast.point_forecast))
        ],
    )


def predict_share(ticker: Ticker, has_shares: bool, *, horizon: int = 10) -> PredictionResult:
    model: ActionClassifier = load_model(MODEL_PATH)
    live_features: Series[Any] = build_live_features(ticker=ticker)
    decision: TradingDecision = model.predict(live_features, has_shares=has_shares, horizon=horizon)
 
    probabilities: list[ActionProbability] = [
        ActionProbability(
            action=_to_action(signal.action),
            probability=signal.probability
        )
        for signal in decision.signals
    ]
    return PredictionResult(
        ticker=ticker.ticker,
        top_action=_to_action(decision.top_signal.action),
        probability=decision.probability,
        decision_margin=decision.decision_margin,
        entropy=decision.entropy,
        confidence=decision.confidence,
        score=decision.score,
        horizon=decision.horizon,
        horizon_unit=decision.horizon_unit,
        action_probabilities=probabilities,
        forecast=_build_forecast_summary(ticker, horizon=horizon),
    )

if __name__ == '__main__':
    result = predict_share(Ticker(ticker='AAPL'), has_shares=False)
    print(result.model_dump_json(indent=2))
