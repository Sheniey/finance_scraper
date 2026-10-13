# ================================================== #
# MODULE: __init__
# ================================================== #


from finance.services.yf_extractor.exceptions import (
    YFExtractorException,
    YFinanceError,
    YFinanceException,
    InvalidTickerError,
    TickerNotFoundError,
)


def __getattr__(name: str):
    if name in {'create_ticker', 'get_data', 'get_info'}:
        from finance.services.yf_extractor import repository
        return getattr(repository, name)
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
