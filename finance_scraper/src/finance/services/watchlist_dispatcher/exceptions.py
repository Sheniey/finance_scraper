"""Exceptions raised by the stateless watchlist dispatcher."""

from finance.services.email.exceptions import (
    EmailConfigurationError,
    InvalidConfigurationError,
)


# ================================================== #
# EXCEPTIONS                                         #
# ================================================== #

class WatchlistDispatcherException(Exception):
    """Base exception for dispatcher configuration and execution errors."""


__all__: list[str] = [
    'EmailConfigurationError',
    'InvalidConfigurationError',
    'WatchlistDispatcherException',
]
