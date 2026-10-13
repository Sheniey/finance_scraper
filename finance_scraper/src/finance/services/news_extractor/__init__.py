# ================================================== #
# MODULE: __init__
# ================================================== #


from finance.services.news_extractor.models import NewsCompilation, NewsArticle
from finance.services.news_extractor.repository import fetch_news
from finance.services.news_extractor.exceptions import (
    NewsExtractorException,
    InvalidMaxNewsValueError,
    NewsSourceNotFoundError,
)
