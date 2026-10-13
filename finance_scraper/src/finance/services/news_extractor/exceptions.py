
# ================================================== #
# BASE EXCEPTIONS                                    #
# ================================================== #

class NewsExtractorException(Exception):
    """Global exception for the news extractor service."""
    pass



# ================================================== #
# CONCRETE EXCEPTIONS                                #
# ================================================== #

class InvalidMaxNewsValueError(NewsExtractorException, ValueError):
    """Error raised when the max_news value is invalid."""
    def __init__(self, max_news: int) -> None:
        self.max_news: int = max_news
        super().__init__(f'Invalid max_news value: {max_news}. It must be a positive integer.')

class NewsSourceNotFoundError(NewsExtractorException):
    """Error raised when a news source is not found."""
    def __init__(self, source_name: str) -> None:
        self.source_name: str = source_name
        super().__init__(f"News source '{source_name}' not found.")
