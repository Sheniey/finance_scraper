# ================================================== #
# MODULE: exceptions
# ================================================== #


class EmailException(Exception):
    """Base exception for email delivery failures."""


EmailError = EmailException


class EmailConfigurationError(EmailException, RuntimeError):
    """Raised when SMTP configuration is incomplete or invalid."""

    def __init__(self, message: str = 'SMTP sender is not configured') -> None:
        self.message: str = message
        super().__init__(message)

class InvalidConfigurationError(EmailException, ValueError):
    """Raised when an email configuration value cannot be parsed."""

    def __init__(self, setting: str, value: object, message: str) -> None:
        self.setting: str = setting
        self.value: object = value
        self.message: str = message
        super().__init__(message)


__all__: list[str] = [
    'EmailConfigurationError',
    'EmailError',
    'EmailException',
    'InvalidConfigurationError',
]
