
from pydantic import BaseModel, Field

from finance.services.stock_analyzer import Metric, Fact


class QuantifiableFacts(BaseModel):
    price: Metric
    dividend_yield: Metric
    dividend_rate: Metric

class DescriptiveFacts(BaseModel):
    ticker: Fact
    name: Fact
    formal_name: Fact
    region: Fact
    currency: Fact
    address: Fact
    industry: Fact
    sector: Fact
    description: Fact
    website: Fact
    dividends: Fact
    last_dividend: Fact
    splits: Fact
    history_10y_1mo: Fact = Field(default_factory=Fact)
    history_5y_1d: Fact = Field(default_factory=Fact)
    history_1y_1d: Fact = Field(default_factory=Fact)
    history_3mo_1d: Fact = Field(default_factory=Fact)
    history_1w_1d: Fact = Field(default_factory=Fact)
    open: Fact = Field(default_factory=Fact)
    high: Fact = Field(default_factory=Fact)
    low: Fact = Field(default_factory=Fact)
    close: Fact = Field(default_factory=Fact)
    phone: Fact = Field(default_factory=Fact)
    quote_type: Fact = Field(default_factory=Fact)


class History10Y1Mo(BaseModel):
    price: Fact = Field(default_factory=Fact)
    revenue: Fact = Field(default_factory=Fact)
    earnings: Fact = Field(default_factory=Fact)
    free_cash_flow: Fact = Field(default_factory=Fact)
    dividends: Fact = Field(default_factory=Fact)
    pe_ratio: Fact = Field(default_factory=Fact)
    price_to_fcf: Fact = Field(default_factory=Fact)
    ev_to_ebitda: Fact = Field(default_factory=Fact)
    price_to_sales: Fact = Field(default_factory=Fact)
    peg_ratio: Fact = Field(default_factory=Fact)
    sp500: Fact = Field(default_factory=Fact)


class Valuation(BaseModel):
    pe_ratio: Metric
    peg_ratio: Metric
    trailing_pe_ratio: Metric
    forward_pe_ratio: Metric
    ev_to_market_cap: Metric
    price_to_fcf: Metric
    ev_to_ebitda: Metric
    ev_to_ebit: Metric
    price_to_book: Metric
    price_to_sales: Metric
    earnings_yield: Metric

class Growth(BaseModel):
    revenue_growth: Metric
    earnings_growth: Metric
    eps_growth: Metric
    revenue_cagr_5y: Metric
    revenue_cagr_10y: Metric
    eps_cagr_5y: Metric
    eps_cagr_10y: Metric
    fcf_cagr_5y: Metric
    fcf_cagr_10y: Metric
    fcf_growth: Metric
    owner_earnings_growth: Metric
    shares_outstanding_growth: Metric
    retained_earnings_growth: Metric

class Profitability(BaseModel):
    profit_margin: Metric
    operating_margin: Metric
    return_on_equity: Metric
    return_on_assets: Metric
    roic: Metric
    roce: Metric
    return_on_equity_5y: Metric
    return_on_equity_10y: Metric
    gross_margin: Metric
    gross_profit: Metric
    ebitda: Metric
    ebitda_margin: Metric

class CashFlow(BaseModel):
    operating_cash_flow: Metric
    capital_expenditures: Metric
    fcf_margin: Metric
    cash_conversion: Metric
    operating_cash_flow_margin: Metric
    owner_earnings: Metric
    owner_earnings_yield: Metric

class FinancialHealth(BaseModel):
    debt_to_equity: Metric
    current_ratio: Metric
    quick_ratio: Metric
    free_cash_flow: Metric
    net_debt: Metric
    net_debt_to_ebitda: Metric

class CapitalAllocation(BaseModel):
    shares_outstanding: Metric
    buyback_yield: Metric
    shareholder_yield: Metric
    retained_earnings: Metric
    acquisition_spending: Metric

class WorkingCapital(BaseModel):
    working_capital: Metric
    change_in_working_capital: Metric
    receivables: Metric
    inventory: Metric
    accounts_payable: Metric

class StockAnalysis(BaseModel):
    quantifiable_facts: QuantifiableFacts
    descriptive_facts: DescriptiveFacts
    valuation: Valuation
    growth: Growth
    profitability: Profitability
    cash_flow: CashFlow
    financial_health: FinancialHealth
    capital_allocation: CapitalAllocation
    working_capital: WorkingCapital
    history_10y_1mo: History10Y1Mo = Field(default_factory=History10Y1Mo)
