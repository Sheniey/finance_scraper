
from dataclasses import dataclass
import numpy as np
import pandas as pd
import yfinance as yf

from datatypes import Ticker
from nexis.config import TRAINING_METADATA
from nexis.errors import (
    EmptyHistoryError,
    EmptyFeaturesError,
    EmptyTrainingDatasetError,
    HistoryDownloadError,
    InsufficientHistoryError,
)
from nexis.actions import ALL_ACTION_LABELS, MODEL_ACTION_LABELS, TradingAction


# ================================================== #
# DATACLASSES                                        #
# ================================================== #

@dataclass(frozen=True)
class DatasetConfig:
    lookback_days: int = TRAINING_METADATA.asset_lookback_days
    horizon_days: int = 5
    move_threshold: float = 0.02

    def __post_init__(self) -> None:
        if self.lookback_days < MIN_FEATURE_HISTORY:
            raise ValueError(
                f'lookback_days must be at least {MIN_FEATURE_HISTORY} '
                'to compute the SMA-200 feature.'
            )
        if self.horizon_days <= 0:
            raise ValueError('horizon_days must be positive.')
        if self.move_threshold < 0:
            raise ValueError('move_threshold must be non-negative.')


# ================================================== #
# CONSTANTS                                          #
# ================================================== #

ACTION_LABELS: tuple[str, ...] = ALL_ACTION_LABELS

FEATURE_COLUMNS: tuple[str, ...] = (
    'ret_1d',
    'ret_5d',
    'ret_10d',
    'log_return',
    'volatility_10d',
    'volatility_20d',
    'sma_5_ratio',
    'sma_20_ratio',
    'sma_50_ratio',
    'sma_200_ratio',
    'ema_20_ratio',
    'ema_50_ratio',
    'rsi_14',
    'macd',
    'macd_signal',
    'macd_hist',
    'atr_14',
    'adx_14',
    'volume_ratio_20d',
    'obv',
    'bollinger_position',
)
MIN_FEATURE_HISTORY: int = 200


# ================================================== #
# HELPERS                                            #
# ================================================== #

def _compute_features(history: pd.DataFrame) -> pd.DataFrame:
    if history.empty:
        raise EmptyHistoryError()

    df: pd.DataFrame = history.copy()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close: pd.Series    = df['Close']
    high: pd.Series     = df['High']
    low: pd.Series      = df['Low']
    volume: pd.Series   = df['Volume']

    features: pd.DataFrame = pd.DataFrame(index=df.index)

    # ===========================================
    # RETURNS
    # ===========================================

    features['ret_1d']      = close.pct_change(1)
    features['ret_5d']      = close.pct_change(5)
    features['ret_10d']     = close.pct_change(10)
    features['log_return']  = np.log(close / close.shift(1))

    # ===========================================
    # VOLATILITY
    # ===========================================

    returns = close.pct_change()

    features['volatility_10d'] = returns.rolling(10).std()
    features['volatility_20d'] = returns.rolling(20).std()

    # ===========================================
    # SMA
    # ===========================================

    sma5    = close.rolling(5).mean()
    sma20   = close.rolling(20).mean()
    sma50   = close.rolling(50).mean()
    sma200  = close.rolling(200).mean()

    features['sma_5_ratio'] = close / sma5 - 1
    features['sma_20_ratio'] = close / sma20 - 1
    features['sma_50_ratio'] = close / sma50 - 1
    features['sma_200_ratio'] = close / sma200 - 1

    # ===========================================
    # EMA
    # ===========================================

    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    features['ema_20_ratio'] = close / ema20 - 1
    features['ema_50_ratio'] = close / ema50 - 1

    # ===========================================
    # RSI (Wilder)
    # ===========================================

    delta   = close.diff()

    gain    = delta.clip(lower=0)
    loss    = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()

    rs  = avg_gain / avg_loss.replace(0, np.nan)

    features['rsi_14'] = 100 - (100 / (1 + rs))

    # ===========================================
    # MACD
    # ===========================================

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()

    macd    = ema12 - ema26
    signal  = macd.ewm(span=9, adjust=False).mean()

    features['macd'] = macd
    features['macd_signal'] = signal
    features['macd_hist'] = macd - signal

    # ===========================================
    # ATR-14
    # ===========================================

    prev_close: pd.Series = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(alpha=1 / 14, adjust=False).mean()

    features['atr_14'] = atr / close

    # ===========================================
    # ADX-14
    # ===========================================

    up_move     = high.diff()
    down_move   = -low.diff()

    plus_dm     = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm    = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    plus_di = (
        100
        * plus_dm.ewm(alpha=1 / 14, adjust=False).mean()
        / atr.replace(0, np.nan)
    )

    minus_di = (
        100
        * minus_dm.ewm(alpha=1 / 14, adjust=False).mean()
        / atr.replace(0, np.nan)
    )

    dx = (
        (plus_di - minus_di).abs()
        / (plus_di + minus_di).replace(0, np.nan)
    ) * 100

    features['adx_14'] = dx.ewm(alpha=1 / 14, adjust=False).mean()

    # ===========================================
    # VOLUME
    # ===========================================

    volume_mean   = volume.rolling(20).mean()

    features['volume_ratio_20d'] = volume / volume_mean - 1

    # ===========================================
    # OBV
    # ===========================================

    direction       = np.sign(close.diff()).fillna(0)

    features['obv'] = (direction * volume).cumsum().pct_change()

    # ===========================================
    # BOLLINGER
    # ===========================================

    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()

    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std

    features['bollinger_position'] = (
        (close - bb_lower)
        / (bb_upper - bb_lower)
    )

    return features.replace([np.inf, -np.inf], np.nan)


def _download_history(
    ticker: Ticker,
    lookback_days: int,
    *,
    minimum_points: int = MIN_FEATURE_HISTORY,
) -> pd.DataFrame:
    history: pd.DataFrame = yf.download(
        ticker.value,
        period=f'{lookback_days}d',
        interval='1d',
        auto_adjust=True,
        progress=False,
    )

    if history.empty:
        raise HistoryDownloadError(ticker=ticker)
    
    if len(history.index) < minimum_points:
        raise InsufficientHistoryError(
            ticker=ticker,
            required_points=minimum_points,
            actual_points=len(history.index),
        )
    
    return history



# ================================================== #
# FEATURES                                           #
# ================================================== #

def build_training_dataset(ticker: Ticker, config: DatasetConfig | None = None) -> pd.DataFrame:
    conf: DatasetConfig = config or DatasetConfig()
    history: pd.DataFrame = _download_history(
        ticker=ticker,
        lookback_days=conf.lookback_days,
        minimum_points=MIN_FEATURE_HISTORY + conf.horizon_days,
    )
    features: pd.DataFrame = _compute_features(history)

    future_return: pd.Series = history['Close'].shift(-conf.horizon_days) / history['Close'] - 1
    dataset: pd.DataFrame = features.copy()
    dataset['future_return'] = future_return
    dataset['target'] = np.where(
        dataset['future_return'] > conf.move_threshold,
        TradingAction.BUY.value,
        np.where(
            dataset['future_return'] < -conf.move_threshold,
            TradingAction.SELL.value,
            TradingAction.HOLD.value,
        ),
    )

    dataset: pd.DataFrame = dataset.dropna()
    if dataset.empty:
        raise EmptyTrainingDatasetError(ticker=ticker)
    
    return dataset


def build_live_features(ticker: Ticker, lookback_days: int = TRAINING_METADATA.asset_lookback_days) -> pd.Series:
    history: pd.DataFrame = _download_history(
        ticker=ticker,
        lookback_days=lookback_days,
        minimum_points=MIN_FEATURE_HISTORY,
    )
    features: pd.DataFrame = _compute_features(history).dropna()

    if features.empty:
        raise EmptyFeaturesError(ticker=ticker)
    
    return features.iloc[-1][list(FEATURE_COLUMNS)]


def build_price_history(ticker: Ticker, lookback_days: int = TRAINING_METADATA.asset_lookback_days) -> pd.Series[float]:
    """
    Raw daily close price series (not technical features), used by
    `TimesFMForecaster` for zero-shot forecasting.
    """

    history: pd.DataFrame = _download_history(
        ticker=ticker,
        lookback_days=lookback_days,
        minimum_points=1,
    )
    close: pd.Series[float] = history['Close']
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:,0]
    return close.rename(ticker.ticker)
