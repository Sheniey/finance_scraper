
from dataclasses import dataclass
from finance.types.report_mode import ReportMode


# ================================================== #
# REPORT CUSTOM PRESETS                              #
# ================================================== #

ALL_SECTIONS: frozenset[str] = frozenset(
    {
        'valuation',
        'profitability',
        'cash_flow',
        'growth',
        'financial_health',
        'capital_allocation',
        'working_capital',
    }
)

CUSTOM_METRIC_NAMES: frozenset[str] = frozenset(
    {
        'pe_ratio',
        'peg_ratio',
        'trailing_pe_ratio',
        'forward_pe_ratio',
        'ev_to_market_cap',
        'ev2market_cap',
        'price_to_fcf',
        'ev_to_ebitda',
        'ev_to_ebit',
        'price_to_book',
        'price_to_sales',
        'earnings_yield',
        'revenue_growth',
        'earnings_growth',
        'eps_growth',
        'revenue_cagr_5y',
        'eps_cagr_5y',
        'fcf_cagr_5y',
        'revenue_cagr_10y',
        'eps_cagr_10y',
        'fcf_cagr_10y',
        'fcf_growth',
        'owner_earnings_growth',
        'shares_outstanding_growth',
        'retained_earnings_growth',
        'return_on_equity',
        'return_on_assets',
        'roic',
        'roce',
        'return_on_equity_5y',
        'return_on_equity_10y',
        'gross_margin',
        'gross_profit',
        'ebitda',
        'ebitda_margin',
        'operating_cash_flow',
        'capital_expenditures',
        'fcf_margin',
        'cash_conversion',
        'operating_cash_flow_margin',
        'owner_earnings',
        'owner_earnings_yield',
        'debt_to_equity',
        'current_ratio',
        'quick_ratio',
        'free_cash_flow',
        'net_debt',
        'net_debt_to_ebitda',
        'shares_outstanding',
        'buyback_yield',
        'shareholder_yield',
        'retained_earnings',
        'acquisition_spending',
        'working_capital',
        'change_in_working_capital',
        'receivables',
        'inventory',
        'accounts_payable',
    }
)

CUSTOM_FEATURE_NAMES: frozenset[str] = frozenset(
    {
        'explanation',
        'dividends_and_splits',
        'dividends',
        'splits',
    }
)

CUSTOM_GRAPH_NAMES: frozenset[str] = frozenset(
    {
        'price_history',
        'relative_performance',
        'drawdown',
        'fair_value',
        'valuation_history',
        'fundamental_growth',
        'dividends_history',
        'fundamental_value',
    }
)



# ================================================== #
# DATACLASSES                                        #
# ================================================== #

@dataclass(frozen=True)
class ReportPreset:
    sections: frozenset[str]
    show_analysis: bool
    show_facts: bool
    show_description: bool
    show_explanation: bool
    show_news: bool



# ================================================== #
# REPORT PROFILE PRESETS                             #
# ================================================== #

PRESETS: dict[ReportMode, ReportPreset] = {
    ReportMode.CLASSIC: ReportPreset(
        sections=ALL_SECTIONS,
        show_analysis=True,
        show_facts=True,
        show_description=True,
        show_explanation=True,
        show_news=False,
    ),
    ReportMode.FULL: ReportPreset(
        sections=ALL_SECTIONS,
        show_analysis=True,
        show_facts=True,
        show_description=True,
        show_explanation=True,
        show_news=True,
    ),
    ReportMode.GROWTH: ReportPreset(
        sections=frozenset({'growth', 'profitability', 'cash_flow'}),
        show_analysis=True,
        show_facts=True,
        show_description=True,
        show_explanation=True,
        show_news=False,
    ),
    ReportMode.VALIDATION: ReportPreset(
        sections=frozenset({'valuation', 'profitability', 'financial_health'}),
        show_analysis=True,
        show_facts=True,
        show_description=True,
        show_explanation=True,
        show_news=False,
    ),
    ReportMode.INFO: ReportPreset(
        sections=frozenset(),
        show_analysis=False,
        show_facts=True,
        show_description=True,
        show_explanation=False,
        show_news=False,
    ),
    ReportMode.CUSTOM: ReportPreset(
        sections=ALL_SECTIONS,
        show_analysis=True,
        show_facts=True,
        show_description=True,
        show_explanation=True,
        show_news=False,
    ),
}


# ================================================== #
# FEATURES - IDK WHY TS HERE                         #
# ================================================== #

def get_preset(mode: ReportMode) -> ReportPreset:
    return PRESETS[mode]
