
from pydantic import BaseModel


# ================================================== #
# TYPE ALIASES                                       #
# ================================================== #

type NewsCompilation = list[NewsArticle]



# ================================================== #
# MODELS                                             #
# ================================================== #

class NewsSource(BaseModel):
    url: str
    name: str | None = None
    region: str | None = None

class NewsArticle(BaseModel):
    title: str
    content_type: str
    source: NewsSource
    summary: str
    author: str = '<Unknown>'
    published_at: str | None = None

    def __str__(self) -> str:
        return f'{self.title} --- {self.summary} --- Made by {self.author} at {self.published_at} from {self.source.name or self.source.url}'
    