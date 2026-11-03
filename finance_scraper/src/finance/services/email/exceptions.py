"""Exceptions raised while delivering a report email."""


class EmailException(Exception):
    """Base exception for report email delivery failures."""

    pass


class EmailDeliveryError(EmailException):
    """Raised when an authorized Google account cannot send a report."""

    pass
