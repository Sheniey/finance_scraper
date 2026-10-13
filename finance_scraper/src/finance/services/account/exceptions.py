
# ================================================== #
# GLOBAL EXCEPTIONS                                  #
# ================================================== #

class AccountException(Exception):
    """Global exception for the account service."""

class AccountSchemaException(RuntimeError):
    """Raised when the account database needs an explicit schema rebuild."""


# ================================================== #
# CUSTOM EXCEPTIONS                                  #
# ================================================== #

class InvalidTickerError(AccountException, ValueError):
    """Raised when an invalid ticker symbol is provided."""

    def __init__(self, message: str = 'Invalid ticker symbol.') -> None:
        self.message: str = message
        super().__init__(message)

class AccountAlreadyExistsError(AccountException, ValueError):
    """Raised when an account already exists."""

    def __init__(self, email: str) -> None:
        self.email: str = email
        super().__init__(f"An account with email '{email}' already exists.")

class AccountNotFoundError(AccountException, LookupError):
    """Raised when an account cannot be found."""

    def __init__(self, identifier: str) -> None:
        self.identifier: str = identifier
        super().__init__(f'Account {identifier!r} does not exist.')
