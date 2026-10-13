
from pydantic import BaseModel
from enum import StrEnum

from datatypes import Ticker
from finance.types.report_mode import ReportMode
from finance.services.stock_analyzer import StockAnalysis
from finance.services.news_extractor import NewsCompilation
from finance.services.account import Account
from finance.services.stock_analyzer import Metric, Fact
from finance.services.ml import PredictionResult


class Reasoning(StrEnum):
    POSITIVE = '+'
    NEUTRAL = '*'
    NEGATIVE = '-'


class ExplanationConfig[A: StrEnum](BaseModel):
    action: A
    possible_actions: list[A]
    account: Account
    ticker: Ticker
    news_compilation: NewsCompilation
    analysis: StockAnalysis
    prediction_result: PredictionResult
    mode: ReportMode = ReportMode.CLASSIC



class Point(BaseModel):
    reasoning: Reasoning
    content: str

    def __str__(self) -> str:
        return f'[{self.reasoning}] {self.content}'


class Explanation(BaseModel):
    summary: str
    points: list[Point]

    def __str__(self) -> str:
        return f"""
{self.summary}

{''.join(f'{point}\n' for point in self.points)}
""".strip()
