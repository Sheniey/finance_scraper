# ================================================== #
# MODULE: exceptions
# ================================================== #


class YFExtractorException(Exception):
    """Global exception for the Yahoo Finance extractor service."""
    pass


class InvalidTickerError(YFExtractorException, ValueError):
    """Raised when an invalid ticker symbol is provided."""

    def __init__(self, ticker: str = '', message: str | None = None) -> None:
        self.ticker: str = ticker
        detail: str = message or f'Ticker symbol {ticker!r} is invalid.'
        super().__init__(detail)


class TickerNotFoundError(YFExtractorException, LookupError):
    """Raised when a ticker symbol is not found."""

    def __init__(self, ticker: str = '') -> None:
        self.ticker: str = ticker
        super().__init__(f'Ticker symbol {ticker!r} was not found.')


YFinanceError = YFExtractorException
YFinanceException = YFExtractorException
