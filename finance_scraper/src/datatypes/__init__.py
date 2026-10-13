"""
Datatypes, "data types", wrappers and adapters package.

This module provides wrappers to handle various data types such as
percentage, money and `YFinance` data with `Pydantic 2.0`.
Also provides some features for easier manipulation and conversion of these data types.

This package wraps and adapts the functionalities provided by `designkit.creational.types`.
"""

from datatypes.percentage import PercentageWrapper as Percentage
from datatypes.money import (
    CurrencyWrapper as Currency,
    MoneyWrapper as Money,
    Currencies,
    to_money,
)
from designkit.creational.toolbox.currency import convert as convert_currency
from datatypes.ticker import (
    Ticker, # it's not same than YFinanceTicker; it represents only the ticker like "AAPL.MX"
    YFinanceDividend,
    YFinanceHistoryPoint,
    HistoricalMetricPoint,
    YFinanceSplit,
    YFinanceStatement,
    YFinanceTicker, # this represents the full YFinance ticker object
    YFinanceTickerInfo,
)


__all__ = [
    'Percentage',
    'Currency',
    'Money',
    'Currencies',
    'to_money',
    'convert_currency',
    'Ticker',
    'YFinanceDividend',
    'YFinanceHistoryPoint',
    'HistoricalMetricPoint',
    'YFinanceSplit',
    'YFinanceStatement',
    'YFinanceTicker',
    'YFinanceTickerInfo',
]
