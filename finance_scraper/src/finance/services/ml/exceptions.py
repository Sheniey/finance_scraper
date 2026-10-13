
# ================================================== #
# BASE EXCEPTIONS                                    #
# ================================================== #

class ModelException(Exception):
    """Global exception for the machine learning service."""
    pass


class InvalidMiddlewareError(ModelException, TypeError):
    """Raised when an invalid middleware is provided."""

    def __init__(self, middleware: object) -> None:
        self.middleware: object = middleware
        super().__init__(f'Invalid middleware: {middleware}. Must be an instance of Middleware.')



# ================================================== #
# EXCEPTION ALIASES                                  #
# ================================================== #

MachineLearningException = ModelException
