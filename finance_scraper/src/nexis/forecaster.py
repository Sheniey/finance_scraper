
import os
import numpy as np
import pandas as pd
from dataclasses import dataclass
from designkit.creational.singleton import singleton
from datetime import date
from typing import Any

from datatypes import Ticker

from nexis.misc.literals import TradingPeriodUnit
from nexis.enums import ForecastTrend
from nexis.models import ForecastResult
from nexis.errors import (
    ForecastGenerationError,
    ForecastModelUnavailableError,
    InsufficientForecastHistoryError,
)


# ================================================== #
# CONSTANTS                                          #
# ================================================== #

# TimesFM 3.0 forecasts nine deciles (0.1 to 0.9), with the median at index 4.
QUANTILE_LEVELS: tuple[float, ...] = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
MEDIAN_QUANTILE_INDEX: int = 4

# Return checkpoints we surface whenever they fit inside the requested horizon.
RETURN_CHECKPOINTS_DAYS: tuple[int, ...] = (1, 5, 10, 20, 30)

# TimesFM's own recommended minimum context length to produce a useful forecast.
MIN_FORECAST_CONTEXT: int = 64

DEFAULT_CHECKPOINT: str = 'google/timesfm-3.0-pytorch'
DEFAULT_MOVE_THRESHOLD: float = 0.02


# ================================================== #
# HELPERS                                            #
# ================================================== #

def _resolve_device() -> str:
    override: str | None = os.getenv('TIMESFM_DEVICE')
    if override:
        return override

    try:
        import torch
    except ImportError:
        return 'cpu'

    return 'cuda' if torch.cuda.is_available() else 'cpu'


def _linear_slope(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0

    x: np.ndarray = np.arange(len(values), dtype=float)
    slope, _intercept = np.polyfit(x, values, 1)
    return float(slope)


def _future_business_days(last_observed: pd.Timestamp, horizon: int) -> tuple[date, ...]:
    future_index: pd.DatetimeIndex = pd.bdate_range(
        start=last_observed, periods=horizon + 1
    )[1:]
    return tuple(timestamp.date() for timestamp in future_index)



# ================================================== #
# FORECASTER                                         #
# ================================================== #

class TimesFMForecaster:
    """
    Thin wrapper around Google's TimesFM 3.0 zero-shot forecasting model.

    Unlike `ActionClassifier`, this model is never trained/fitted on our
    data: it is a pretrained foundation model used purely for inference.
    """

    def __init__(
        self,
        checkpoint: str = DEFAULT_CHECKPOINT,
        device: str | None = None,
        move_threshold: float = DEFAULT_MOVE_THRESHOLD,
    ) -> None:
        self.__checkpoint: str = checkpoint
        self.__device: str = device or _resolve_device()
        self.__move_threshold: float = move_threshold
        self.__evaluator: object | None = None

    def _load_evaluator(self) -> object:
        if self.__evaluator is not None:
            return self.__evaluator

        try:
            from timesfm3 import ModelConfig, TimesFM3Evaluator
        except ImportError as e:
            raise ForecastModelUnavailableError(str(e)) from e

        config = ModelConfig(
            checkpoint_path=self.__checkpoint,
            per_core_batch_size=1,
            device=self.__device,
        )
        try:
            self.__evaluator = TimesFM3Evaluator(config)
        except Exception as e:
            raise ForecastModelUnavailableError(str(e)) from e

        return self.__evaluator

    def forecast(
        self,
        ticker: Ticker,
        history: pd.Series[float],
        horizon: int,
        *,
        horizon_unit: TradingPeriodUnit = 'day',
    ) -> ForecastResult:
        if horizon <= 0:
            raise ValueError('horizon must be positive.')

        series: pd.Series = history.dropna()
        if len(series) < MIN_FORECAST_CONTEXT:
            raise InsufficientForecastHistoryError(
                ticker=ticker,
                required_points=MIN_FORECAST_CONTEXT,
                actual_points=len(series),
            )

        evaluator = self._load_evaluator()
        context: np.ndarray = series.to_numpy(dtype=np.float32)

        outputs: list[Any]
        try:
            outputs = list(
                evaluator.predict_batch(
                    [context],
                    horizon=horizon,
                    return_quantiles=True,
                    use_symmetric_averaging=False,
                )
            )
        except Exception as e:
            raise ForecastGenerationError(ticker=ticker, reason=str(e)) from e

        output: Any = outputs[0]
        point_forecast: np.ndarray = np.asarray(output.forecast, dtype=float)
        quantile_matrix: np.ndarray = np.asarray(output.quantiles, dtype=float)

        last_price: float = float(series.iloc[-1])
        future_dates: tuple[date, ...] = _future_business_days(
            pd.Timestamp(series.index[-1]), horizon
        )

        quantiles: dict[str, tuple[float, ...]] = {
            f'q{int(level * 100)}': tuple(quantile_matrix[:, index].tolist())
            for index, level in enumerate(QUANTILE_LEVELS)
        }

        returns: dict[int, float] = {
            checkpoint: float(point_forecast[checkpoint - 1] / last_price - 1)
            for checkpoint in RETURN_CHECKPOINTS_DAYS
            if checkpoint <= horizon
        }
        returns.setdefault(horizon, float(point_forecast[-1] / last_price - 1))

        volatility: float = (
            float(np.std(np.diff(point_forecast) / point_forecast[:-1]))
            if horizon > 1
            else 0.0
        )
        uncertainty: float = float(
            (quantile_matrix[-1, -1] - quantile_matrix[-1, 0]) / last_price
        )
        
        final_return: float = returns[horizon]
        trend_signal: ForecastTrend
        if final_return > self.__move_threshold:
            trend_signal = ForecastTrend.UP
        elif final_return < -self.__move_threshold:
            trend_signal = ForecastTrend.DOWN
        else:
            trend_signal = ForecastTrend.FLAT

        return ForecastResult(
            ticker=ticker.ticker,
            horizon=horizon,
            horizon_unit=horizon_unit,
            last_price=last_price,
            dates=future_dates,
            point_forecast=tuple(point_forecast.tolist()),
            quantiles=quantiles,
            returns=returns,
            slope=_linear_slope(point_forecast) / last_price,
            volatility=volatility,
            uncertainty=uncertainty,
            trend_signal=trend_signal,
        )


__all__ = [
    'DEFAULT_CHECKPOINT',
    'ForecastHorizonUnit',
    'ForecastResult',
    'ForecastTrend',
    'TimesFMForecaster'
]
