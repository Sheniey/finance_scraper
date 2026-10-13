
from pydantic import BaseModel, Field

from datatypes import Ticker, YFinanceTicker
from finance.types.report_mode import ReportMode
from finance.services.stock_analyzer import StockAnalysis, DescriptiveFacts, QuantifiableFacts
from finance.services.news_extractor import NewsCompilation
from finance.services.account import Account
from finance.services.ml import PredictionResult
from finance.services.llm import Explanation


# ================================================== #
# MODELS                                             #
# ================================================== #

class Report(BaseModel):
    account: Account
    ticker: Ticker
    news_compilation: NewsCompilation
    analysis: StockAnalysis
    prediction_result: PredictionResult
    explanation: Explanation = Field(default='')
    charts: bool = Field(default=True, description='Indicates whether the report includes charts.')
    has_explanation: bool = Field(default=False, description='Indicates whether the report includes an explanation.')
    mode: ReportMode = Field(default=ReportMode.CLASSIC)
    custom_report: list[str] = Field(default_factory=list)
    
    def get_news(self) -> str:
        return '\n'.join(f'- {news.summary}' for news in self.news_compilation)

    @property
    def raw_info(self) -> YFinanceTicker:
        return self.ticker.extract_data()

    @property
    def quantifiable_facts(self) -> QuantifiableFacts:
        return self.analysis.quantifiable_facts

    @property
    def descriptive_facts(self) -> DescriptiveFacts:
        return self.analysis.descriptive_facts
