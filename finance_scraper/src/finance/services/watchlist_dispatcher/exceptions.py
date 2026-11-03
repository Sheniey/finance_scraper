"""Exceptions raised by the stateless watchlist dispatcher."""

# ================================================== #
# EXCEPTIONS                                         #
# ================================================== #

class WatchlistDispatcherException(Exception):
    """Base exception for dispatcher configuration and execution errors."""


__all__: list[str] = [
    'WatchlistDispatcherException',
]
