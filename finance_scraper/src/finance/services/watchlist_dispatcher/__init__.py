"""Stateless watchlist report dispatching service."""


# ================================================== #
# MODULE: __init__
# ================================================== #

from finance.services.watchlist_dispatcher.dispatcher import (
    AttachmentRenderer,
    DispatchResult,
    ReportGenerator,
    WatchlistDispatcher,
)
from finance.services.watchlist_dispatcher.exceptions import (
    EmailConfigurationError,
    InvalidConfigurationError,
    WatchlistDispatcherException,
)

__all__: list[str] = [
    'AttachmentRenderer',
    'DispatchResult',
    'ReportGenerator',
    'WatchlistDispatcher',
    'EmailConfigurationError',
    'InvalidConfigurationError',
    'WatchlistDispatcherException',
]
