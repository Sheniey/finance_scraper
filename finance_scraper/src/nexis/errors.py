
from pathlib import Path

from datatypes import Ticker


# ================================================== #
# GLOBAL EXCEPTION                                   #
# ================================================== #

class ModelException(Exception):
    """Base exception for the ML module."""


# ================================================== #
# CUSTOM EXCEPTIONS                                  #
# ================================================== #

class HistoryDownloadError(ModelException):
    def __init__(self, ticker: Ticker) -> None:
        self.ticker: Ticker = ticker
        self.message: str = f'Cannot download historical data for "{ticker}".'
        super().__init__(self.message)

class EmptyHistoryError(ModelException):
    def __init__(self) -> None:
        self.message: str = 'Cannot construct features because the historical data is empty.'
        super().__init__(self.message)


class InsufficientHistoryError(ModelException):
    def __init__(self, ticker: Ticker, required_points: int, actual_points: int) -> None:
        self.ticker: Ticker = ticker
        self.required_points: int = required_points
        self.actual_points: int = actual_points
        self.message: str = (
            f'Insufficient history for "{ticker}". '
            f'At least {required_points} daily candles are required, but only {actual_points} were obtained.'
        )
        super().__init__(self.message)


class EmptyFeaturesError(ModelException):
    def __init__(self, ticker: Ticker) -> None:
        self.ticker: Ticker = ticker
        self.message: str = f'Not enough data for inference in "{ticker}".'
        super().__init__(self.message)


class EmptyTrainingDatasetError(ModelException):
    def __init__(self, ticker: Ticker) -> None:
        self.ticker: Ticker = ticker
        self.message: str = f'Empty dataset for "{ticker}". Adjust lookback/horizon/threshold.'
        super().__init__(self.message)


class MissingTargetColumnError(ModelException):
    def __init__(self) -> None:
        self.message: str = 'The dataset must include the "target" column.'
        super().__init__(self.message)


class MissingFeatureColumnsError(ModelException):
    def __init__(self, missing_columns: list[str]) -> None:
        self.missing_columns: list[str] = missing_columns
        self.message: str = f'Missing required columns for training: {missing_columns}'
        super().__init__(self.message)


class InvalidDecisionContextError(ModelException):
    def __init__(self) -> None:
        self.message: str = 'Could not resolve the decision context for prediction.'
        super().__init__(self.message)


class InvalidModelProbabilitiesError(ModelException):
    def __init__(self) -> None:
        self.message: str = 'No valid probabilities were obtained from the classifier.'
        super().__init__(self.message)


class ModelArtifactNotFoundError(ModelException):
    def __init__(self, artifact_path: Path) -> None:
        self.artifact_path: Path = artifact_path
        self.message: str = f'No trained model exists at "{artifact_path}". Run nexis.trainer first.'
        super().__init__(self.message)


class InvalidModelArtifactError(ModelException):
    def __init__(self, artifact_path: Path) -> None:
        self.artifact_path: Path = artifact_path
        self.message: str = f'The artifact "{artifact_path}" does not contain a valid ActionClassifier.'
        super().__init__(self.message)


class ForecastModelUnavailableError(ModelException):
    def __init__(self, reason: str) -> None:
        self.reason: str = reason
        self.message: str = (
            'The TimesFM forecasting model is unavailable: '
            f'{reason}. Install it with "pip install git+https://github.com/google-research/timesfm.git" '
            'along with "torch".'
        )
        super().__init__(self.message)


class InsufficientForecastHistoryError(ModelException):
    def __init__(self, ticker: Ticker, required_points: int, actual_points: int) -> None:
        self.ticker: Ticker = ticker
        self.required_points: int = required_points
        self.actual_points: int = actual_points
        self.message: str = (
            f'Insufficient history to generate a forecast for "{ticker}". '
            f'At least {required_points} daily candles are required, but only {actual_points} were obtained.'
        )
        super().__init__(self.message)


class ForecastGenerationError(ModelException):
    def __init__(self, ticker: Ticker, reason: str) -> None:
        self.ticker: Ticker = ticker
        self.reason: str = reason
        self.message: str = f'Failed to generate forecast for "{ticker}": {reason}.'
        super().__init__(self.message)
