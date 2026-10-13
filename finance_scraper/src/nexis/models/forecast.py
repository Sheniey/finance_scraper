
import pandas as pd
from datetime import date
from dataclasses import dataclass, field
from designkit.creational.singleton import singleton

from nexis.misc.literals import TradingPeriodUnit
from nexis.enums.forecast import ForecastTrend


# ================================================== #
# MODELS                                             #
# ================================================== #

@singleton
@dataclass(frozen=True)
class ForecastResult:
    ticker: str
    horizon: int
    horizon_unit: TradingPeriodUnit
    last_price: float
    dates: tuple[date, ...]
    point_forecast: tuple[float, ...]
    quantiles: dict[str, tuple[float, ...]]
    returns: dict[int, float]
    slope: float
    volatility: float
    uncertainty: float
    trend_signal: ForecastTrend

    @property
    def expected_return(self) -> float:
        """Expected return at the requested horizon (point forecast)."""
        return self.returns[self.horizon]

    def to_frame(self) -> pd.DataFrame:
        """
        Returns a tidy `date/predicted/qXX...` frame, ready to be charted
        by another component alongside the historical price series.
        """

        frame: pd.DataFrame = pd.DataFrame(
            {'date': self.dates, 'predicted': self.point_forecast}
        )
        for quantile_name, values in sorted(self.quantiles.items()):
            frame[quantile_name] = values
        return frame
