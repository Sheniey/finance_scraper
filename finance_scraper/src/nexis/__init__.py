"""
Nexis, machine learning package.

It essentially provides a predictive model using `scikit-learn` classifiers:
`LightGBM`, `RandomForest` and `CatBoost`; linked with the Google Research model
for financial time series forecasting, `Google Times FM`.

See `nexis/settings.yaml` to adjust the hyperparameters and other settings of the predictive model. So, deep train it.
"""

from nexis.backtester import BacktestMetrics, run_backtest
from nexis.actions import (
    ALL_ACTION_LABELS,
    MODEL_ACTION_LABELS,
    MODEL_ACTIONS,
    TradingAction,
)
from nexis.classifier import (
    ActionClassifier,
    TradingDecision,
    TradingSignal,
)
from nexis.errors import (
    EmptyHistoryError,
    EmptyFeaturesError,
    EmptyTrainingDatasetError,
    HistoryDownloadError,
    InsufficientHistoryError,
    InvalidModelArtifactError,
    ModelException,
    ModelArtifactNotFoundError,
)
from nexis.predictor import load_model


__all__ = [
    'ActionClassifier',
    'ALL_ACTION_LABELS',
    'BacktestMetrics',
    'EmptyHistoryError',
    'EmptyFeaturesError',
    'EmptyTrainingDatasetError',
    'HistoryDownloadError',
    'InsufficientHistoryError',
    'InvalidModelArtifactError',
    'ModelException',
    'MODEL_ACTION_LABELS',
    'MODEL_ACTIONS',
    'ModelArtifactNotFoundError',
    'TradingAction',
    'TradingDecision',
    'TradingSignal',
    'load_model',
    'run_backtest',
]
