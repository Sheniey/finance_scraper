
import re
from datetime import date
from yfinance import Ticker as YFinanceTicker
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


# ================================================== #
# EXCEPTIONS                                         #
# ================================================== #

class InvalidTickerError(ValueError):
    """Raised when an invalid ticker symbol is provided."""
    pass


# ================================================== #
# REGEX PATTERNS                                     #
# ================================================== #

SHARE_SYMBOL_PATTERN: re.Pattern = re.compile(r'^[A-Z]+[A-Z0-9\.\-]*$')


# ================================================== #
# MODELS                                             #
# ================================================== #

class Ticker(BaseModel):
    ticker: str

    # this normalizes the ticker to uppercase and validates it against the regex pattern
    @field_validator('ticker')
    def validate_ticker(value: str) -> str:
        value = value.upper()

        if not SHARE_SYMBOL_PATTERN.match(value):
            raise InvalidTickerError(
                f'Share symbol format <{value}> is invalid. Must be uppercase letters, numbers, dots, or dashes, e.g. AAPL, FMX23.MX, NVDA'
            )

        return value

    def __str__(self) -> str:
        return self.ticker

    def extract_data(self) -> YFinanceTicker:
        return YFinanceTicker(self.ticker)

    def dump(self) -> YFinanceTickerInfo:
        from finance.services.yf_extractor.repository import build_info

        return build_info(self.extract_data())

    @property
    def symbol(self) -> str:
        return self.ticker.split('.', 1)[0]

    @property
    def region(self) -> str:
        if '.' in self.ticker:
            return self.ticker.split('.', 1)[1]
        return 'US'
    
    @property
    def value(self) -> str:
        return self.ticker


StatementValue = int | float | None


class YFinanceHistoryPoint(BaseModel):
    date: date
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    adjusted_close: float | None = None
    volume: int | None = None


class HistoricalMetricPoint(BaseModel):
    date: date
    value: float | None = None


class YFinanceDividend(BaseModel):
    date: date
    amount: float


class YFinanceSplit(BaseModel):
    date: date
    ratio: float | str


class YFinanceStatement(BaseModel):
    values: dict[str, dict[str, StatementValue]] = Field(default_factory=dict)


class YFinanceTickerInfo(BaseModel):
    address1: Optional[str | dict[str, str]] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    industryKey: Optional[str] = None
    industryDisp: Optional[str] = None
    sector: Optional[str] = None
    sectorKey: Optional[str] = None
    sectorDisp: Optional[str] = None
    longBusinessSummary: Optional[str] = None
    fullTimeEmployees: Optional[int] = None
    companyOfficers: Optional[list[dict[str, str | int | float | bool]]] = None
    auditRisk: Optional[int] = None
    boardRisk: Optional[int] = None
    compensationRisk: Optional[int] = None
    shareHolderRightsRisk: Optional[int] = None
    overallRisk: Optional[int] = None
    governanceEpochDate: Optional[int] = None
    compensationAsOfEpochDate: Optional[int] = None
    irWebsite: Optional[str] = None
    executiveTeam: Optional[list[dict[str, str | int | float | bool]]] = None
    maxAge: Optional[int] = None
    priceHint: Optional[int] = None
    previousClose: Optional[float] = None
    open: Optional[float] = None
    low: Optional[float] = None
    high: Optional[float] = None
    close: Optional[float] = None
    dayLow: Optional[float] = None
    dayHigh: Optional[float] = None
    regularMarketPreviousClose: Optional[float] = None
    regularMarketOpen: Optional[float] = None
    regularMarketDayLow: Optional[float] = None
    regularMarketDayHigh: Optional[float] = None
    dividendRate: Optional[float] = None
    dividendYield: Optional[float] = None
    exDividendDate: Optional[int] = None
    payoutRatio: Optional[float] = None
    fiveYearAvgDividendYield: Optional[float] = None
    beta: Optional[float] = None
    trailingPE: Optional[float] = None
    forwardPE: Optional[float] = None
    volume: Optional[int] = None
    regularMarketVolume: Optional[int] = None
    averageVolume: Optional[int] = None
    averageVolume10days: Optional[int] = None
    averageDailyVolume10Day: Optional[int] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    bidSize: Optional[int] = None
    askSize: Optional[int] = None
    marketCap: Optional[int] = None
    nonDilutedMarketCap: Optional[int] = None
    fiftyTwoWeekLow: Optional[float] = None
    fiftyTwoWeekHigh: Optional[float] = None
    allTimeHigh: Optional[float] = None
    allTimeLow: Optional[float] = None
    priceToSalesTrailing12Months: Optional[float] = None
    fiftyDayAverage: Optional[float] = None
    twoHundredDayAverage: Optional[float] = None
    trailingAnnualDividendRate: Optional[float] = None
    trailingAnnualDividendYield: Optional[float] = None
    currency: Optional[str] = None
    tradeable: Optional[bool] = None
    enterpriseValue: Optional[int] = None
    profitMargins: Optional[float] = None
    floatShares: Optional[int] = None
    sharesOutstanding: Optional[int] = None
    sharesShort: Optional[int] = None
    sharesShortPriorMonth: Optional[int] = None
    sharesShortPreviousMonthDate: Optional[int] = None
    dateShortInterest: Optional[int] = None
    sharesPercentSharesOut: Optional[float] = None
    heldPercentInsiders: Optional[float] = None
    heldPercentInstitutions: Optional[float] = None
    shortRatio: Optional[float] = None
    shortPercentOfFloat: Optional[float] = None
    impliedSharesOutstanding: Optional[int] = None
    bookValue: Optional[float] = None
    priceToBook: Optional[float] = None
    lastFiscalYearEnd: Optional[int] = None
    nextFiscalYearEnd: Optional[int] = None
    mostRecentQuarter: Optional[int] = None
    earningsQuarterlyGrowth: Optional[float] = None
    netIncomeToCommon: Optional[int] = None
    trailingEps: Optional[float] = None
    forwardEps: Optional[float] = None
    pegRatio: Optional[float] = None
    lastSplitFactor: Optional[str] = None
    lastSplitDate: Optional[int] = None
    enterpriseToRevenue: Optional[float] = None
    enterpriseToEbitda: Optional[float] = None
    fiftyTwoWeekChange: Optional[float] = None
    SandP52WeekChange: Optional[float] = None
    lastDividendValue: Optional[float] = None
    lastDividendDate: Optional[int] = None
    quoteType: Optional[str] = None
    currentPrice: Optional[float] = None
    targetHighPrice: Optional[float] = None
    targetLowPrice: Optional[float] = None
    targetMeanPrice: Optional[float] = None
    targetMedianPrice: Optional[float] = None
    recommendationMean: Optional[float] = None
    recommendationKey: Optional[str] = None
    numberOfAnalystOpinions: Optional[int] = None
    totalCash: Optional[int] = None
    totalCashPerShare: Optional[float] = None
    ebitda: Optional[int] = None
    totalDebt: Optional[int] = None
    quickRatio: Optional[float] = None
    currentRatio: Optional[float] = None
    totalRevenue: Optional[int] = None
    debtToEquity: Optional[float] = None
    revenuePerShare: Optional[float] = None
    returnOnAssets: Optional[float] = None
    returnOnEquity: Optional[float] = None
    grossProfits: Optional[int] = None
    freeCashflow: Optional[int] = None
    operatingCashflow: Optional[int] = None
    earningsGrowth: Optional[float] = None
    revenueGrowth: Optional[float] = None
    grossMargins: Optional[float] = None
    ebitdaMargins: Optional[float] = None
    operatingMargins: Optional[float] = None
    financialCurrency: Optional[str] = None
    symbol: Optional[str] = None
    language: Optional[str] = None
    region: Optional[str] = None
    typeDisp: Optional[str] = None
    quoteSourceName: Optional[str] = None
    triggerable: Optional[bool] = None
    customPriceAlertConfidence: Optional[str] = None
    hasPrePostMarketData: Optional[bool] = None
    firstTradeDateMilliseconds: Optional[int] = None
    postMarketChangePercent: Optional[float] = None
    postMarketPrice: Optional[float] = None
    postMarketChange: Optional[float] = None
    regularMarketChange: Optional[float] = None
    regularMarketDayRange: Optional[str] = None
    fullExchangeName: Optional[str] = None
    averageDailyVolume3Month: Optional[int] = None
    fiftyTwoWeekLowChange: Optional[float] = None
    fiftyTwoWeekLowChangePercent: Optional[float] = None
    fiftyTwoWeekRange: Optional[str] = None
    fiftyTwoWeekHighChange: Optional[float] = None
    fiftyTwoWeekHighChangePercent: Optional[float] = None
    fiftyTwoWeekChangePercent: Optional[float] = None
    dividendDate: Optional[int] = None
    earningsTimestamp: Optional[int] = None
    earningsTimestampStart: Optional[int] = None
    earningsTimestampEnd: Optional[int] = None
    earningsCallTimestampStart: Optional[int] = None
    earningsCallTimestampEnd: Optional[int] = None
    isEarningsDateEstimate: Optional[bool] = None
    epsTrailingTwelveMonths: Optional[float] = None
    epsForward: Optional[float] = None
    epsCurrentYear: Optional[float] = None
    priceEpsCurrentYear: Optional[float] = None
    fiftyDayAverageChange: Optional[float] = None
    fiftyDayAverageChangePercent: Optional[float] = None
    twoHundredDayAverageChange: Optional[float] = None
    twoHundredDayAverageChangePercent: Optional[float] = None
    sourceInterval: Optional[int] = None
    exchangeDataDelayedBy: Optional[int] = None
    corporateActions: Optional[list[dict[str, Any]]] = None
    postMarketTime: Optional[int] = None
    regularMarketTime: Optional[int] = None
    exchange: Optional[str] = None
    messageBoardId: Optional[str] = None
    exchangeTimezoneName: Optional[str] = None
    exchangeTimezoneShortName: Optional[str] = None
    gmtOffSetMilliseconds: Optional[int] = None
    market: Optional[str] = None
    esgPopulated: Optional[bool] = None
    marketState: Optional[str] = None
    regularMarketChangePercent: Optional[float] = None
    regularMarketPrice: Optional[float] = None
    averageAnalystRating: Optional[str] = None
    cryptoTradeable: Optional[bool] = None
    shortName: Optional[str] = None
    longName: Optional[str] = None
    displayName: Optional[str] = None
    trailingPegRatio: Optional[float] = None
    turnover: Optional[float] = None
    history: list[YFinanceHistoryPoint] = Field(default_factory=list)
    history_5y_1d: list[YFinanceHistoryPoint] = Field(default_factory=list)
    history_1y_1d: list[YFinanceHistoryPoint] = Field(default_factory=list)
    history_3mo_1d: list[YFinanceHistoryPoint] = Field(default_factory=list)
    history_1w_1d: list[YFinanceHistoryPoint] = Field(default_factory=list) 
    sp500_history: list[YFinanceHistoryPoint] = Field(default_factory=list)
    dividendHistory: list[YFinanceDividend] = Field(default_factory=list)
    splitHistory: list[YFinanceSplit] = Field(default_factory=list)
    incomeStatement: YFinanceStatement = Field(default_factory=YFinanceStatement)
    balanceSheet: YFinanceStatement = Field(default_factory=YFinanceStatement)
    cashFlow: YFinanceStatement = Field(default_factory=YFinanceStatement)
