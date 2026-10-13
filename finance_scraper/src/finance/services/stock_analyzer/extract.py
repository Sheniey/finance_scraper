# ================================================== #
# MODULE: extract
# ================================================== #


# Informal Facts
from finance.services.stock_analyzer.facts.name         import extractor as name
from finance.services.stock_analyzer.facts.formal_name  import extractor as formal_name
from finance.services.stock_analyzer.facts.currency     import extractor as currency
from finance.services.stock_analyzer.facts.symbol       import extractor as symbol
from finance.services.stock_analyzer.facts.region       import extractor as region
from finance.services.stock_analyzer.facts.sector       import extractor as sector
from finance.services.stock_analyzer.facts.ticker       import extractor as ticker
from finance.services.stock_analyzer.facts.description  import extractor as description
from finance.services.stock_analyzer.facts.website      import extractor as website
from finance.services.stock_analyzer.facts.dividends    import extractor as dividends
from finance.services.stock_analyzer.facts.industry     import extractor as industry
from finance.services.stock_analyzer.facts.address      import extractor as address

# Facts
from finance.services.stock_analyzer.facts.price         import extractor as price
from finance.services.stock_analyzer.facts.last_dividend import extractor as last_dividend
from finance.services.stock_analyzer.facts.dividend_rate import extractor as dividend_rate
from finance.services.stock_analyzer.facts.dividend_yield import extractor as dividend_yield
from finance.services.stock_analyzer.facts.splits        import extractor as splits
from finance.services.stock_analyzer.facts.history_10y_1mo import extractor as history_10y_1mo
from finance.services.stock_analyzer.facts.history_5y_1d import extractor as history_5y_1d
from finance.services.stock_analyzer.facts.history_1y_1d import extractor as history_1y_1d
from finance.services.stock_analyzer.facts.history_3mo_1d import extractor as history_3mo_1d
from finance.services.stock_analyzer.facts.history_1w_1d import extractor as history_1w_1d
from finance.services.stock_analyzer.facts.ohlc          import (
    open_extractor as open,
    high_extractor as high,
    low_extractor as low,
    close_extractor as close,
)
from finance.services.stock_analyzer.facts.phone         import extractor as phone
from finance.services.stock_analyzer.facts.quote_type    import extractor as quote_type

# Valuation Metrics
from finance.services.stock_analyzer.metrics.pe_ratio       import extractor as pe_ratio
from finance.services.stock_analyzer.metrics.peg_ratio      import extractor as peg_ratio
from finance.services.stock_analyzer.metrics.forward_pe     import extractor as forward_pe_ratio
from finance.services.stock_analyzer.metrics.trailing_pe    import extractor as trailing_pe_ratio
from finance.services.stock_analyzer.metrics.ev2market_cap  import extractor as ev_to_market_cap

# Growth Metrics
from finance.services.stock_analyzer.metrics.revenue_growth     import extractor as revenue_growth
from finance.services.stock_analyzer.metrics.earnings_growth    import extractor as earnings_growth
from finance.services.stock_analyzer.metrics.eps_growth         import extractor as eps_growth

# Profitability Metrics
from finance.services.stock_analyzer.metrics.return_on_equity   import extractor as return_on_equity
from finance.services.stock_analyzer.metrics.return_on_assets   import extractor as return_on_assets
from finance.services.stock_analyzer.metrics.profit_margin      import extractor as profit_margin
from finance.services.stock_analyzer.metrics.operating_margin   import extractor as operating_margin

# Financial Health Metrics
from finance.services.stock_analyzer.metrics.debt2equity    import extractor as debt_to_equity
from finance.services.stock_analyzer.metrics.current_ratio  import extractor as current_ratio
from finance.services.stock_analyzer.metrics.quick_ratio    import extractor as quick_ratio
from finance.services.stock_analyzer.metrics.free_cash_flow import extractor as free_cash_flow

# Derived metrics
from finance.services.stock_analyzer.metrics.derived import (
    price_to_fcf,
    ev_to_ebitda,
    ev_to_ebit,
    price_to_book,
    price_to_sales,
    earnings_yield,
    roic,
    roce,
    return_on_equity_5y,
    return_on_equity_10y,
    gross_margin,
    gross_profit,
    ebitda,
    ebitda_margin,
    operating_cash_flow,
    capital_expenditures,
    fcf_margin,
    fcf_growth,
    cash_conversion,
    operating_cash_flow_margin,
    owner_earnings,
    owner_earnings_growth,
    owner_earnings_yield,
    net_debt,
    net_debt_to_ebitda,
    revenue_cagr_5y,
    revenue_cagr_10y,
    eps_cagr_5y,
    eps_cagr_10y,
    fcf_cagr_5y,
    fcf_cagr_10y,
    shares_outstanding,
    shares_outstanding_growth,
    buyback_yield,
    shareholder_yield,
    retained_earnings,
    retained_earnings_growth,
    acquisition_spending,
    working_capital,
    change_in_working_capital,
    receivables,
    inventory,
    accounts_payable,
)
