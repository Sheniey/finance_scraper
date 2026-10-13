# ================================================== #
# MODULE: exceptions
# ================================================== #


class DatabaseException(RuntimeError):
    """Raised when a database operation cannot be completed."""


class DatabaseConfigurationError(DatabaseException, ValueError):
    """Raised when a database URL or pool setting is invalid."""


class DatabaseIntegrityError(DatabaseException):
    """Raised when a database constraint is violated."""


class DatabaseAlreadyOpenError(DatabaseException):
    """Raised when another process owns the local Turso Sync replica."""


class DatabaseSyncError(DatabaseException):
    """Raised when a local replica cannot synchronize with Turso."""


LibSQLDatabaseException = DatabaseException
LibSQLIntegrityError = DatabaseIntegrityError


__all__: list[str] = [
    'DatabaseException',
    'DatabaseConfigurationError',
    'DatabaseIntegrityError',
    'DatabaseAlreadyOpenError',
    'DatabaseSyncError',
    'LibSQLDatabaseException',
    'LibSQLIntegrityError',
]
