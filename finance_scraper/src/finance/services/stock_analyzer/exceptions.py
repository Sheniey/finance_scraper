
class StockAnalyzerException(Exception):
    """Global exception for the stock analyzer service."""
    pass


class DefinitionError(StockAnalyzerException):
    """Raised when a stock-analysis definition is invalid."""
    pass


class MnemonicNotFoundError(StockAnalyzerException, KeyError):
    """Raised when a definition mnemonic is not found."""

    def __init__(self, mnemonic: str) -> None:
        self.mnemonic: str = mnemonic
        super().__init__(f'Mnemonic "{mnemonic}" not found in definition map.')


class InvalidMetricThresholdError(StockAnalyzerException, TypeError):
    """Raised when a metric threshold has an invalid type."""

    def __init__(self, threshold: object, metric_value: object) -> None:
        self.threshold: object = threshold
        self.metric_value: object = metric_value
        super().__init__(
            f'Invalid threshold type: {threshold} for metric value {metric_value}'
        )


class MissingMetricValueError(StockAnalyzerException, ValueError):
    """Raised when a missing metric value is used numerically."""

    def __init__(self, value: object) -> None:
        self.value: object = value
        super().__init__(f'Cannot convert missing metric value to a number: {value!r}')


class CurrencyMismatchError(StockAnalyzerException, ValueError):
    """Raised when monetary metrics use different currencies."""

    def __init__(self, previous_currency: str, current_currency: str) -> None:
        self.previous_currency: str = previous_currency
        self.current_currency: str = current_currency
        super().__init__('Cannot compare monetary metrics with different currencies.')


class InvalidRatingRuleError(StockAnalyzerException, ValueError):
    """Raised when a rating rule has an invalid threshold."""

    def __init__(self, threshold: object) -> None:
        self.threshold: object = threshold
        super().__init__(
            f'Invalid threshold type for rating rule: {threshold} (expected numeric)'
        )
