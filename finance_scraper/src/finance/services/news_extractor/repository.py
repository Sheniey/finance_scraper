
from designkit.behavioral.typing import Assertion

from datatypes.ticker import YFinanceTicker

from finance.services.news_extractor.models import NewsCompilation, NewsArticle, NewsSource
from finance.services.news_extractor.exceptions import InvalidMaxNewsValueError, NewsSourceNotFoundError


# ================================================== #
# NEWS EXTRACTOR                                     #
# ================================================== #

def fetch_news(data: YFinanceTicker, max_news: int = 10) -> NewsCompilation:
    Assertion(data).must_be(YFinanceTicker)
    Assertion(max_news).must_be(int)
    Assertion(max_news).must_comply(lambda x: x > 0, custom_expt=InvalidMaxNewsValueError(max_news))

    news: list[dict] = data.news
    if not news:
        return []

    return [
        NewsArticle(
            title=item['content']['title'],
            content_type=item['content']['contentType'],
            source=NewsSource(
                url=item['content']['canonicalUrl']['url'],
                region=item['content']['canonicalUrl']['region'],
                name=item['content']['provider']['displayName']
            ),
            summary=item['content']['summary'],
            author=item['content']['provider']['displayName'] or '<Unknown>',
            published_at=item['content']['pubDate']
        )
        for item in news[:max_news]
    ]
