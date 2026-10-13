
import json
from typing import Any
from datetime import datetime
from designkit.behavioral.typing import Assertion

from finance.config import envm, LLM_MAX_TOKENS, LLM_TEMPERATURE
from finance.services.account import has_positive_position
from finance.services.stock_analyzer import StockAnalysis
from finance.types.report_presets import ReportPreset, get_preset
from finance.services.llm.config import ROLE_TEMPLATE, STYLE_TEMPLATES, OUTPUT_TEMPLATE as OUTPUT
from finance.services.llm.models import ExplanationConfig, Explanation, Point, Reasoning
from finance.services.llm.strategy import LLMService, Response, create_llm_service
from finance.services.llm.exceptions import (
    EmptyExplanationError,
    InvalidExplanationError,
    LLMInitializationError,
)


type PromptEntry = tuple[str, str, object]

def fmt_bool(value: bool) -> str:
    return 'Yes' if value else 'No'
    
def build_system(config: ExplanationConfig) -> str:
    BASE_ROLE: str = ROLE_TEMPLATE.format(
        actions=', '.join(config.possible_actions),
        language=config.account.language.name
    )
    STYLE: str = STYLE_TEMPLATES[config.account.language.style]

    return f'{BASE_ROLE}\n\n{STYLE}\n\n{OUTPUT}'


def _normalized_custom_report(config: ExplanationConfig) -> set[str]:
    return {
        item.strip().lower()
        for item in config.account.custom_report
    }


def _include_metric(
    config: ExplanationConfig,
    preset: ReportPreset,
    custom_report: set[str],
    section: str,
    metric: str,
) -> bool:
    if section not in preset.sections:
        return False
    if config.mode.value != 'custom':
        return True
    return metric.lower() in custom_report


def _build_block(
    config: ExplanationConfig,
    preset: ReportPreset,
    custom_report: set[str],
    title: str,
    section: str,
    entries: list[PromptEntry],
) -> str:
    lines: list[str] = [
        f'{label}: {value}'
        for metric, label, value in entries
        if _include_metric(config, preset, custom_report, section, metric)
    ]
    if not lines:
        return ''
    return f'{title}\n----------\n' + '\n'.join(lines)


def _build_analysis_blocks(
    config: ExplanationConfig,
    analysis: StockAnalysis,
    preset: ReportPreset,
    custom_report: set[str],
) -> list[str]:
    return [
        _build_block(
            config,
            preset,
            custom_report,
            'Valuation',
            'valuation',
            [
                ('pe_ratio', 'P/E Ratio', analysis.valuation.pe_ratio),
                ('peg_ratio', 'PEG Ratio', analysis.valuation.peg_ratio),
                ('trailing_pe_ratio', 'Trailing P/E Ratio', analysis.valuation.trailing_pe_ratio),
                ('forward_pe_ratio', 'Forward P/E Ratio', analysis.valuation.forward_pe_ratio),
                ('ev_to_market_cap', 'EV / Market Cap', analysis.valuation.ev_to_market_cap),
                ('price_to_fcf', 'Price / FCF', analysis.valuation.price_to_fcf),
                ('ev_to_ebitda', 'EV / EBITDA', analysis.valuation.ev_to_ebitda),
                ('ev_to_ebit', 'EV / EBIT', analysis.valuation.ev_to_ebit),
                ('price_to_book', 'Price / Book', analysis.valuation.price_to_book),
                ('price_to_sales', 'Price / Sales', analysis.valuation.price_to_sales),
                ('earnings_yield', 'Earnings Yield', analysis.valuation.earnings_yield),
            ],
        ),
        _build_block(
            config,
            preset,
            custom_report,
            'Growth',
            'growth',
            [
                ('revenue_growth', 'Revenue Growth', analysis.growth.revenue_growth),
                ('earnings_growth', 'Earnings Growth', analysis.growth.earnings_growth),
                ('eps_growth', 'EPS Growth', analysis.growth.eps_growth),
                ('revenue_cagr_5y', 'Revenue CAGR (5Y)', analysis.growth.revenue_cagr_5y),
                ('revenue_cagr_10y', 'Revenue CAGR (10Y)', analysis.growth.revenue_cagr_10y),
                ('eps_cagr_5y', 'EPS CAGR (5Y)', analysis.growth.eps_cagr_5y),
                ('eps_cagr_10y', 'EPS CAGR (10Y)', analysis.growth.eps_cagr_10y),
                ('fcf_cagr_5y', 'FCF CAGR (5Y)', analysis.growth.fcf_cagr_5y),
                ('fcf_cagr_10y', 'FCF CAGR (10Y)', analysis.growth.fcf_cagr_10y),
                ('fcf_growth', 'FCF Growth', analysis.growth.fcf_growth),
                ('owner_earnings_growth', 'Owner Earnings Growth', analysis.growth.owner_earnings_growth),
                ('shares_outstanding_growth', 'Shares Outstanding Growth', analysis.growth.shares_outstanding_growth),
                ('retained_earnings_growth', 'Retained Earnings Growth', analysis.growth.retained_earnings_growth),
            ],
        ),
        _build_block(
            config,
            preset,
            custom_report,
            'Profitability',
            'profitability',
            [
                ('profit_margin', 'Profit Margin', analysis.profitability.profit_margin),
                ('operating_margin', 'Operating Margin', analysis.profitability.operating_margin),
                ('return_on_equity', 'Return on Equity', analysis.profitability.return_on_equity),
                ('return_on_assets', 'Return on Assets', analysis.profitability.return_on_assets),
                ('roic', 'ROIC', analysis.profitability.roic),
                ('roce', 'ROCE', analysis.profitability.roce),
                ('return_on_equity_5y', 'Average ROE (5Y)', analysis.profitability.return_on_equity_5y),
                ('return_on_equity_10y', 'Average ROE (10Y)', analysis.profitability.return_on_equity_10y),
                ('gross_margin', 'Gross Margin', analysis.profitability.gross_margin),
                ('gross_profit', 'Gross Profit', analysis.profitability.gross_profit),
                ('ebitda', 'EBITDA', analysis.profitability.ebitda),
                ('ebitda_margin', 'EBITDA Margin', analysis.profitability.ebitda_margin),
            ],
        ),
        _build_block(
            config,
            preset,
            custom_report,
            'Cash Flow',
            'cash_flow',
            [
                ('operating_cash_flow', 'Operating Cash Flow', analysis.cash_flow.operating_cash_flow),
                ('capital_expenditures', 'Capital Expenditures', analysis.cash_flow.capital_expenditures),
                ('fcf_margin', 'FCF Margin', analysis.cash_flow.fcf_margin),
                ('cash_conversion', 'Cash Conversion', analysis.cash_flow.cash_conversion),
                ('operating_cash_flow_margin', 'Operating Cash Flow Margin', analysis.cash_flow.operating_cash_flow_margin),
                ('owner_earnings', 'Estimated Owner Earnings', analysis.cash_flow.owner_earnings),
                ('owner_earnings_yield', 'Estimated Owner Earnings Yield', analysis.cash_flow.owner_earnings_yield),
            ],
        ),
        _build_block(
            config,
            preset,
            custom_report,
            'Financial Health',
            'financial_health',
            [
                ('debt_to_equity', 'Debt to Equity', analysis.financial_health.debt_to_equity),
                ('current_ratio', 'Current Ratio', analysis.financial_health.current_ratio),
                ('quick_ratio', 'Quick Ratio', analysis.financial_health.quick_ratio),
                ('free_cash_flow', 'Free Cash Flow', analysis.financial_health.free_cash_flow),
                ('net_debt', 'Net Debt', analysis.financial_health.net_debt),
                ('net_debt_to_ebitda', 'Net Debt / EBITDA', analysis.financial_health.net_debt_to_ebitda),
            ],
        ),
        _build_block(
            config,
            preset,
            custom_report,
            'Capital Allocation',
            'capital_allocation',
            [
                ('shares_outstanding', 'Shares Outstanding', analysis.capital_allocation.shares_outstanding),
                ('buyback_yield', 'Buyback Yield', analysis.capital_allocation.buyback_yield),
                ('shareholder_yield', 'Shareholder Yield', analysis.capital_allocation.shareholder_yield),
                ('retained_earnings', 'Retained Earnings', analysis.capital_allocation.retained_earnings),
                ('acquisition_spending', 'Acquisition Spending', analysis.capital_allocation.acquisition_spending),
            ],
        ),
        _build_block(
            config,
            preset,
            custom_report,
            'Working Capital',
            'working_capital',
            [
                ('working_capital', 'Working Capital', analysis.working_capital.working_capital),
                ('change_in_working_capital', 'Change in Working Capital', analysis.working_capital.change_in_working_capital),
                ('receivables', 'Receivables', analysis.working_capital.receivables),
                ('inventory', 'Inventory', analysis.working_capital.inventory),
                ('accounts_payable', 'Accounts Payable', analysis.working_capital.accounts_payable),
            ],
        ),
    ]


def _build_dividends_block(
    config: ExplanationConfig,
    analysis: StockAnalysis,
    custom_report: set[str],
) -> str:
    if (
        config.mode.value == 'custom'
        and not custom_report.intersection({'dividends_and_splits', 'dividends', 'splits'})
    ):
        return ''

    return f'''Dividends
----------
Dividend Yield: {analysis.quantifiable_facts.dividend_yield}
Dividend Rate: {analysis.quantifiable_facts.dividend_rate}
Dividends: {analysis.descriptive_facts.dividends}'''


def _build_news_section(config: ExplanationConfig) -> str:
    return ''.join(
        f'News Item {i + 1}: {fact}\n'
        for i, fact in enumerate(config.news_compilation)
    )


def _build_raw_result_lines(config: ExplanationConfig) -> str:
    return ', '.join(
        f'{ap.action} ({ap.probability})'
        for ap in config.prediction_result.action_probabilities
    )

def build_user(config: ExplanationConfig) -> str:
    analysis: StockAnalysis = config.analysis
    has_shares: bool = has_positive_position(
        config.account,
        config.ticker,
    )
    preset: ReportPreset = get_preset(config.mode)
    custom_report = _normalized_custom_report(config)
    analysis_blocks = _build_analysis_blocks(config, analysis, preset, custom_report)
    selected_analysis: str = '\n\n'.join(block for block in analysis_blocks if block)
    dividends_block = _build_dividends_block(config, analysis, custom_report)

    return f'''
Metadata
----------
Current Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Account
----------
Name: {config.account.name}
Language: {config.account.language.name} ({config.account.language.style})
Does he own {config.ticker.symbol} stock?: {fmt_bool(has_shares)}

Ticker
----------
Symbol: {config.ticker.symbol}
Region: {config.ticker.region}
Industry: {analysis.descriptive_facts.industry}
Sector: {analysis.descriptive_facts.sector}
Name: {analysis.descriptive_facts.formal_name}

{dividends_block}

{selected_analysis}

News
----------
{_build_news_section(config)}

Machine Learning Model Prediction
----------
Top Action: {config.prediction_result.top_action} (Probability: {config.prediction_result.probability})
Possible Actions: {', '.join(config.possible_actions)}
Raw Results: {_build_raw_result_lines(config)}

Machine Learning Model Metadata
----------
Horizon: {config.prediction_result.horizon} {config.prediction_result.horizon_unit}s
Decision Margin: {config.prediction_result.decision_margin}
Confidence: {config.prediction_result.confidence}
Entropy: {config.prediction_result.entropy}
Total Score: {config.prediction_result.score} (*Uses some properties such as confidence, entropy, etc... to calculate the overall score*)
'''.strip()


llm_service: LLMService | None = None
client: LLMService | None = None
client_provider: str | None = None


def init_client() -> None:
    global client, client_provider, llm_service
    llm_service = create_llm_service()
    client = llm_service
    client_provider = llm_service.preferred_provider


async def chat(system_prompt: str, user_prompt: str, **options: Any) -> Response:
    global client_provider

    service: LLMService | None = llm_service
    if service is None:
        init_client()
        service = llm_service
    if service is None:
        raise LLMInitializationError()

    response: Response = await service.chat(
        system_prompt,
        user_prompt,
        **options,
    )
    client_provider = service.last_provider
    return response


def _parse_explanation(raw_response: str) -> Explanation:
    response_text: str = raw_response.strip()
    if response_text.startswith('```') and response_text.endswith('```'):
        response_lines: list[str] = response_text.splitlines()
        if response_lines and response_lines[0].strip().startswith('```'):
            response_lines = response_lines[1:]
        if response_lines and response_lines[-1].strip() == '```':
            response_lines = response_lines[:-1]
        response_text = '\n'.join(response_lines).strip()

    try:
        raw_explanation: Any = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise InvalidExplanationError('LLM returned invalid JSON for the explanation') from e
    if not isinstance(raw_explanation, dict):
        raise InvalidExplanationError('LLM explanation must be a JSON object')

    summary: Any = raw_explanation.get('summary')
    if not isinstance(summary, str) or not summary.strip():
        raise InvalidExplanationError(
            'LLM explanation must contain a non-empty summary'
        )

    raw_points: Any = raw_explanation.get('points')
    if not isinstance(raw_points, list) or len(raw_points) < 3:
        raise InvalidExplanationError(
            'LLM explanation must contain at least three points'
        )

    points: list[Point] = []
    for index, raw_point in enumerate(raw_points, start=1):
        if not isinstance(raw_point, dict):
            raise InvalidExplanationError(
                f'LLM explanation point {index} must be an object'
            )
        content: Any = raw_point.get('content')
        if not isinstance(content, str) or not content.strip():
            raise InvalidExplanationError(
                f'LLM explanation point {index} must contain non-empty content'
            )

        reasoning_value: Any = raw_point.get('reasoning', 'neutral')
        reasoning: Reasoning = Reasoning.NEUTRAL
        if isinstance(reasoning_value, str):
            normalized_reasoning: str = reasoning_value.strip().upper()
            reasoning = Reasoning.__members__.get(
                normalized_reasoning,
                Reasoning.NEUTRAL,
            )
            if reasoning is Reasoning.NEUTRAL:
                for candidate in Reasoning:
                    if reasoning_value.strip() == candidate.value:
                        reasoning = candidate
                        break
        points.append(Point(reasoning=reasoning, content=content))

    return Explanation(summary=summary, points=points)


@envm.run_in('dev')
def _dev_explanation() -> Explanation | None:
    return Explanation(
        summary='The analysis suggests that the stock is currently overvalued based on its P/E ratio and PEG ratio. However, the company has strong growth prospects and a solid financial position.',
        points=[
            Point(
                reasoning=Reasoning.NEGATIVE,
                content='The P/E ratio of 30.5 indicates that the stock is overvalued compared to the industry average of 20.'
            ),
            Point(
                reasoning=Reasoning.NEGATIVE,
                content='The PEG ratio of 1.8 suggests that the stock\'s price is high relative to its earnings growth.'
            ),
            Point(
                reasoning=Reasoning.NEUTRAL,
                content='The company has a strong revenue growth of 15% over the past 5 years, indicating good growth prospects.'
            ),
            Point(
                reasoning=Reasoning.POSITIVE,
                content='The company has a low debt-to-equity ratio of 0.3, indicating a solid financial position.'
            ),
        ]
    )

async def explain_action(config: ExplanationConfig) -> Explanation:
    response: Response | None = _dev_explanation()
    if response is not None:
        return response

    response: Response = await chat(
        system_prompt=build_system(config),
        user_prompt=build_user(config),
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
        json_mode=True,
    )
    if response.message is None:
        raise EmptyExplanationError()
    return _parse_explanation(response.message)
