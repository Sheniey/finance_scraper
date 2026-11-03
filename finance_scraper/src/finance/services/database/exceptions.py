
# ================================================== # 
# GLOBAL EXCEPTIONS                                  #
# ================================================== #

class DatabaseException(RuntimeError):
    """Raised when a database operation cannot be completed."""


# ================================================== #
# SPECIFIC EXCEPTIONS                                #
# ================================================== #

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
