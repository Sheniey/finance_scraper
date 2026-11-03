from datetime import date
import re
from typing import Literal

from pydantic import BaseModel, Field, PositiveInt, field_validator

from datatypes.ticker import Ticker
from finance.services.account.models import Stock

from api.schemas.base import OKResponse


_REGION_PATTERN: re.Pattern[str] = re.compile(r'^[A-Z0-9-]{2,8}$')
_CURRENCY_PATTERN: re.Pattern[str] = re.compile(r'^[A-Z]{3}$')


class PortfolioTradeCreate(BaseModel):
    action: Literal['BUY', 'SELL']
    ticker: str = Field(min_length=1, max_length=20)
    region: str = Field(default='US', min_length=2, max_length=8)
    currency: str = Field(default='USD', min_length=3, max_length=3)
    price: float = Field(gt=0, allow_inf_nan=False)
    quantity: PositiveInt
    date: date

    @field_validator('ticker')
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        normalized: str = value.strip().upper()
        if '.' in normalized:
            raise ValueError('ticker must not include a region suffix')
        return Ticker(ticker=normalized).ticker

    @field_validator('region')
    @classmethod
    def normalize_region(cls, value: str) -> str:
        normalized: str = value.strip().upper()
        if not _REGION_PATTERN.fullmatch(normalized):
            raise ValueError('region must be a 2-8 character market code')
        return normalized

    @field_validator('currency')
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized: str = value.strip().upper()
        if not _CURRENCY_PATTERN.fullmatch(normalized):
            raise ValueError('currency must be a three-letter code')
        return normalized


class PortfolioResponse(OKResponse):
    portfolio: list[Stock]
