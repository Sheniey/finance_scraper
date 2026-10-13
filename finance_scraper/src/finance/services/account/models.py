
from typing import Literal, Self
from uuid import UUID, uuid4

from designkit.behavioral.typing import classname
from pydantic import BaseModel, EmailStr, Field, PositiveInt, field_validator, model_validator

from finance.config import DEFAULT_LANGUAGE
from finance.types.language import Language
from finance.types.report_mode import ReportMode
from finance.services.account.exceptions import InvalidTickerError
from finance.services.account.data.patterns import SYMBOL_PATTERN


# ================================================== #
# TYPE ALIASES                                       #
# ================================================== #

type Date = str
type Watchlist = list[WatchlistItem | None]
type Portfolio = list[Stock | None]



# ================================================== #
# MODELS                                             #
# ================================================== #

class WatchlistItem(BaseModel):
    ticker: str
    region: str = 'US'
    mode: ReportMode = ReportMode.CLASSIC
    llm_explanation: bool = False
    charts: bool = True
    horizon: PositiveInt = 10
    enabled: bool = True

    @field_validator('ticker', 'region')
    @classmethod
    def normalize_symbol_part(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise InvalidTickerError('ticker and region must not be blank')
        return normalized

    @property
    def symbol(self) -> str:
        if '.' in self.ticker:
            return self.ticker
        
        if self.region in {'US', 'USD'}:
            return self.ticker
        
        return f'{self.ticker}.{self.region}'

    @model_validator(mode='after')
    def validate_ticker(self) -> Self:
        if not SYMBOL_PATTERN.match(self.symbol):
            raise InvalidTickerError(
                f'Ticker symbol format <{self.symbol}> is invalid. '
                f'Must be uppercase letters, numbers, dots, or dashes. '
                f'e.g. AAPL, FMX23.MX, NVDA'
            )
        return self

class Action(BaseModel):
    action: Literal['BUY', 'SELL']
    price: float
    quantity: int
    date: Date

class Stock(BaseModel):
    ticker: str
    region: str
    currency: str
    actions: list[Action]

    def __str__(self) -> str:
        return f'{self.ticker}.{self.region} ({self.currency})'

class Account(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    email: EmailStr
    account_id: UUID | None = None
    role: str = 'user'
    language: Language = Field(default_factory=lambda: Language(**DEFAULT_LANGUAGE))
    watchlist: Watchlist = Field(default_factory=list)
    portfolio: Portfolio = Field(default_factory=list)
    custom_report: list[str] = Field(default_factory=list)

    def __str__(self) -> str:
        return f'{self.name} <{self.email}>'

    def __repr__(self) -> str:
        return f'{classname(self)}(name={self.name}, email={self.email}, role={self.role})'

    def add_to_watchlist(self, item: WatchlistItem) -> None:
        if not any(watch_item and watch_item.symbol == item.symbol for watch_item in self.watchlist):
            self.watchlist.append(item)
            
