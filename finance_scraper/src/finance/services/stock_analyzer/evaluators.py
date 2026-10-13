
# Informal Facts
from finance.services.stock_analyzer.facts.name         import EVALUATOR as NAME_EVALUATOR
from finance.services.stock_analyzer.facts.formal_name  import EVALUATOR as FORMAL_NAME_EVALUATOR
from finance.services.stock_analyzer.facts.currency     import EVALUATOR as CURRENCY_EVALUATOR
from finance.services.stock_analyzer.facts.symbol       import EVALUATOR as SYMBOL_EVALUATOR
from finance.services.stock_analyzer.facts.region       import EVALUATOR as REGION_EVALUATOR
from finance.services.stock_analyzer.facts.sector       import EVALUATOR as SECTOR_EVALUATOR
from finance.services.stock_analyzer.facts.ticker       import EVALUATOR as TICKER_EVALUATOR
from finance.services.stock_analyzer.facts.description  import EVALUATOR as DESCRIPTION_EVALUATOR
from finance.services.stock_analyzer.facts.website      import EVALUATOR as WEBSITE_EVALUATOR
from finance.services.stock_analyzer.facts.dividends     import EVALUATOR as DIVIDENDS_EVALUATOR
from finance.services.stock_analyzer.facts.industry     import EVALUATOR as INDUSTRY_EVALUATOR
from finance.services.stock_analyzer.facts.address      import EVALUATOR as ADDRESS_EVALUATOR

# Facts
from finance.services.stock_analyzer.facts.price         import EVALUATOR as PRICE_EVALUATOR
from finance.services.stock_analyzer.facts.last_dividend import EVALUATOR as LAST_DIVIDEND_EVALUATOR
from finance.services.stock_analyzer.facts.dividend_rate import EVALUATOR as DIVIDEND_RATE_EVALUATOR
from finance.services.stock_analyzer.facts.dividend_yield import EVALUATOR as DIVIDEND_YIELD_EVALUATOR
from finance.services.stock_analyzer.facts.splits        import EVALUATOR as SPLITS_EVALUATOR
from finance.services.stock_analyzer.facts.history_10y_1mo import EVALUATOR as HISTORY_EVALUATOR

# Valuation Metrics
from finance.services.stock_analyzer.metrics.pe_ratio       import EVALUATOR as PE_RATIO_EVALUATOR
from finance.services.stock_analyzer.metrics.peg_ratio      import EVALUATOR as PEG_RATIO_EVALUATOR
from finance.services.stock_analyzer.metrics.forward_pe     import EVALUATOR as FORWARD_PE_EVALUATOR
from finance.services.stock_analyzer.metrics.trailing_pe    import EVALUATOR as TRAILING_PE_EVALUATOR
from finance.services.stock_analyzer.metrics.ev2market_cap  import EVALUATOR as EV_TO_MARKET_CAP_EVALUATOR

# Growth Metrics
from finance.services.stock_analyzer.metrics.revenue_growth     import EVALUATOR as REVENUE_GROWTH_EVALUATOR
from finance.services.stock_analyzer.metrics.earnings_growth    import EVALUATOR as EARNINGS_GROWTH_EVALUATOR
from finance.services.stock_analyzer.metrics.eps_growth         import EVALUATOR as EPS_GROWTH_EVALUATOR

# Profitability Metrics
from finance.services.stock_analyzer.metrics.return_on_equity   import EVALUATOR as RETURN_ON_EQUITY_EVALUATOR
from finance.services.stock_analyzer.metrics.return_on_assets   import EVALUATOR as RETURN_ON_ASSETS_EVALUATOR
from finance.services.stock_analyzer.metrics.profit_margin      import EVALUATOR as PROFIT_MARGIN_EVALUATOR
from finance.services.stock_analyzer.metrics.operating_margin   import EVALUATOR as OPERATING_MARGIN_EVALUATOR

# Financial Health Metrics
from finance.services.stock_analyzer.metrics.debt2equity    import EVALUATOR as DEBT_TO_EQUITY_EVALUATOR
from finance.services.stock_analyzer.metrics.current_ratio  import EVALUATOR as CURRENT_RATIO_EVALUATOR
from finance.services.stock_analyzer.metrics.quick_ratio    import EVALUATOR as QUICK_RATIO_EVALUATOR
from finance.services.stock_analyzer.metrics.free_cash_flow import EVALUATOR as FREE_CASH_FLOW_EVALUATOR

# Derived metrics
from finance.services.stock_analyzer.metrics.derived import EVALUATOR as DERIVED_EVALUATOR

PRICE_TO_FCF_EVALUATOR = DERIVED_EVALUATOR
EV_TO_EBITDA_EVALUATOR = DERIVED_EVALUATOR
EV_TO_EBIT_EVALUATOR = DERIVED_EVALUATOR
PRICE_TO_BOOK_EVALUATOR = DERIVED_EVALUATOR
PRICE_TO_SALES_EVALUATOR = DERIVED_EVALUATOR
EARNINGS_YIELD_EVALUATOR = DERIVED_EVALUATOR
ROIC_EVALUATOR = DERIVED_EVALUATOR
ROCE_EVALUATOR = DERIVED_EVALUATOR
RETURN_ON_EQUITY_5Y_EVALUATOR = DERIVED_EVALUATOR
RETURN_ON_EQUITY_10Y_EVALUATOR = DERIVED_EVALUATOR
GROSS_MARGIN_EVALUATOR = DERIVED_EVALUATOR
GROSS_PROFIT_EVALUATOR = DERIVED_EVALUATOR
EBITDA_EVALUATOR = DERIVED_EVALUATOR
EBITDA_MARGIN_EVALUATOR = DERIVED_EVALUATOR
OPERATING_CASH_FLOW_EVALUATOR = DERIVED_EVALUATOR
CAPITAL_EXPENDITURES_EVALUATOR = DERIVED_EVALUATOR
FCF_MARGIN_EVALUATOR = DERIVED_EVALUATOR
FCF_GROWTH_EVALUATOR = DERIVED_EVALUATOR
CASH_CONVERSION_EVALUATOR = DERIVED_EVALUATOR
OPERATING_CASH_FLOW_MARGIN_EVALUATOR = DERIVED_EVALUATOR
OWNER_EARNINGS_EVALUATOR = DERIVED_EVALUATOR
OWNER_EARNINGS_GROWTH_EVALUATOR = DERIVED_EVALUATOR
OWNER_EARNINGS_YIELD_EVALUATOR = DERIVED_EVALUATOR
NET_DEBT_EVALUATOR = DERIVED_EVALUATOR
NET_DEBT_TO_EBITDA_EVALUATOR = DERIVED_EVALUATOR
REVENUE_CAGR_5Y_EVALUATOR = DERIVED_EVALUATOR
REVENUE_CAGR_10Y_EVALUATOR = DERIVED_EVALUATOR
EPS_CAGR_5Y_EVALUATOR = DERIVED_EVALUATOR
EPS_CAGR_10Y_EVALUATOR = DERIVED_EVALUATOR
FCF_CAGR_5Y_EVALUATOR = DERIVED_EVALUATOR
FCF_CAGR_10Y_EVALUATOR = DERIVED_EVALUATOR
SHARES_OUTSTANDING_EVALUATOR = DERIVED_EVALUATOR
SHARES_OUTSTANDING_GROWTH_EVALUATOR = DERIVED_EVALUATOR
BUYBACK_YIELD_EVALUATOR = DERIVED_EVALUATOR
SHAREHOLDER_YIELD_EVALUATOR = DERIVED_EVALUATOR
RETAINED_EARNINGS_EVALUATOR = DERIVED_EVALUATOR
RETAINED_EARNINGS_GROWTH_EVALUATOR = DERIVED_EVALUATOR
ACQUISITION_SPENDING_EVALUATOR = DERIVED_EVALUATOR
WORKING_CAPITAL_EVALUATOR = DERIVED_EVALUATOR
CHANGE_IN_WORKING_CAPITAL_EVALUATOR = DERIVED_EVALUATOR
RECEIVABLES_EVALUATOR = DERIVED_EVALUATOR
INVENTORY_EVALUATOR = DERIVED_EVALUATOR
ACCOUNTS_PAYABLE_EVALUATOR = DERIVED_EVALUATOR
