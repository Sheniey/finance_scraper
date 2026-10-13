
from dataclasses import dataclass
from datetime import date, datetime
from html import escape
from math import ceil
from pathlib import Path
from typing import Literal, Any

from reportlab.lib import colors, pagesizes
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.colors import Color
from reportlab.lib.styles import ParagraphStyle
from reportlab.graphics.shapes import Drawing, Image, Rect, String
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.legends import Legend
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    ListFlowable,
    ListItem
)

from datatypes import (
    Money, Percentage, Ticker,
    HistoricalMetricPoint, YFinanceHistoryPoint
)
from finance import investopedia_links as wiki
from finance.config import APP_AUTHOR, APP_NAME, APP_NAME_CODING, LICENSE, LICENSE_TEXT, Theme, lru_cache
from finance.services.i18n import i18n, translate as ui_translate
from finance.services.i18n.models import Translation
from finance.services.llm import Explanation, Reasoning
from finance.services.ml import PredictionResult
from finance.services.reporter import Report
from finance.services.stock_analyzer import Fact, Metric, MetricGrade, MetricStatus
from finance.services.stock_analyzer.schema import DescriptiveFacts, QuantifiableFacts
from finance.types import Language, ReportPreset, get_preset
from finance.renderers.utils import normalize_output
from finance.renderers.pdf.colors import (
    ACCENT_COLOR,
    AWFUL_COLOR,
    BAD_COLOR,
    CARD_COLOR,
    CHART_GRID_COLOR,
    CHART_PRIMARY_COLOR,
    CHART_QUATERNARY_COLOR,
    CHART_SECONDARY_COLOR,
    CHART_TERTIARY_COLOR,
    COVER_LINE_COLOR,
    COVER_MUTED_COLOR,
    EXCELLENT_COLOR,
    GAIN_COLOR,
    GOOD_COLOR,
    INK_COLOR,
    LINK_COLOR,
    MEH_COLOR,
    MUTED_COLOR,
    NEGATIVE_COLOR,
    NEUTRAL_COLOR,
    PAGE_BACKGROUND,
    RULE_COLOR,
    SURFACE_COLOR,
    VERY_BAD_COLOR,
    VERY_GOOD_COLOR,
    WHITE_COLOR,
)
from finance.renderers.pdf.styles import build_styles
# ================================================== #
# TYPES                                              #
# ================================================== #

type MetricKind = Literal['currency', 'percent', 'multiple', 'number', 'integer']


# ================================================== #
# DATACLASSES                                        #
# ================================================== #

@dataclass(frozen=True)
class MetricSpec:
    section: str
    field: str
    mnemonic: str
    fallback: str
    kind: MetricKind
    link: str | None = None


@dataclass(frozen=True)
class ChartSeries:
    name: str
    values: list[tuple[int, float]]
    color: Color


# ================================================== #
# CONSTANTS                                          #
# ================================================== #

METRIC_SPECS: tuple[MetricSpec, ...] = (
    MetricSpec('valuation', 'pe_ratio', 'valuation.pe_ratio', 'P/E Ratio', 'multiple', wiki.PE_RATIO_LINK),
    MetricSpec('valuation', 'peg_ratio', 'valuation.peg_ratio', 'PEG Ratio', 'multiple', wiki.PEG_RATIO_LINK),
    MetricSpec('valuation', 'trailing_pe_ratio', 'valuation.trailing_pe_ratio', 'Trailing P/E', 'multiple', wiki.PE_RATIO_LINK),
    MetricSpec('valuation', 'forward_pe_ratio', 'valuation.forward_pe_ratio', 'Forward P/E', 'multiple', wiki.PE_RATIO_LINK),
    MetricSpec('valuation', 'ev_to_market_cap', 'valuation.ev2market_cap', 'EV/Market Cap', 'multiple', wiki.EV_TO_MARKET_CAP_LINK),
    MetricSpec('valuation', 'price_to_fcf', 'valuation.price_to_fcf', 'Price/FCF', 'multiple', wiki.FREE_CASH_FLOW_LINK),
    MetricSpec('valuation', 'ev_to_ebitda', 'valuation.ev_to_ebitda', 'EV/EBITDA', 'multiple', wiki.EV_TO_EBITDA_LINK),
    MetricSpec('valuation', 'ev_to_ebit', 'valuation.ev_to_ebit', 'EV/EBIT', 'multiple', wiki.EV_TO_EBIT_LINK),
    MetricSpec('valuation', 'price_to_book', 'valuation.price_to_book', 'Price/Book', 'multiple', wiki.PRICE_TO_BOOK_LINK),
    MetricSpec('valuation', 'price_to_sales', 'valuation.price_to_sales', 'Price/Sales', 'multiple', wiki.PRICE_TO_SALES_LINK),
    MetricSpec('valuation', 'earnings_yield', 'valuation.earnings_yield', 'Earnings Yield', 'percent', wiki.EARNINGS_YIELD_LINK),
    MetricSpec('growth', 'revenue_growth', 'growth.revenue_growth', 'Revenue Growth', 'percent', wiki.REVENUE_GROWTH_LINK),
    MetricSpec('growth', 'earnings_growth', 'growth.earnings_growth', 'Earnings Growth', 'percent', wiki.EARNINGS_GROWTH_LINK),
    MetricSpec('growth', 'eps_growth', 'growth.eps_growth', 'EPS Growth', 'percent', wiki.EPS_GROWTH_LINK),
    MetricSpec('growth', 'revenue_cagr_5y', 'growth.revenue_cagr_5y', 'Revenue CAGR 5Y', 'percent', wiki.REVENUE_CAGR_LINK),
    MetricSpec('growth', 'revenue_cagr_10y', 'growth.revenue_cagr_10y', 'Revenue CAGR 10Y', 'percent', wiki.REVENUE_CAGR_LINK),
    MetricSpec('growth', 'eps_cagr_5y', 'growth.eps_cagr_5y', 'EPS CAGR 5Y', 'percent', wiki.EPS_CAGR_LINK),
    MetricSpec('growth', 'eps_cagr_10y', 'growth.eps_cagr_10y', 'EPS CAGR 10Y', 'percent', wiki.EPS_CAGR_LINK),
    MetricSpec('growth', 'fcf_cagr_5y', 'growth.fcf_cagr_5y', 'FCF CAGR 5Y', 'percent', wiki.FCF_CAGR_LINK),
    MetricSpec('growth', 'fcf_cagr_10y', 'growth.fcf_cagr_10y', 'FCF CAGR 10Y', 'percent', wiki.FCF_CAGR_LINK),
    MetricSpec('growth', 'fcf_growth', 'growth.fcf_growth', 'FCF Growth', 'percent', wiki.FCF_GROWTH_LINK),
    MetricSpec('growth', 'owner_earnings_growth', 'growth.owner_earnings_growth', 'Owner Earnings Growth', 'percent', wiki.OWNER_EARNINGS_GROWTH_LINK),
    MetricSpec('growth', 'shares_outstanding_growth', 'growth.shares_outstanding_growth', 'Shares Outstanding Growth', 'percent', wiki.SHARES_OUTSTANDING_GROWTH_LINK),
    MetricSpec('growth', 'retained_earnings_growth', 'growth.retained_earnings_growth', 'Retained Earnings Growth', 'percent', wiki.RETAINED_EARNINGS_GROWTH_LINK),
    MetricSpec('profitability', 'profit_margin', 'profitability.profit_margin', 'Profit Margin', 'percent'),
    MetricSpec('profitability', 'operating_margin', 'profitability.operating_margin', 'Operating Margin', 'percent'),
    MetricSpec('profitability', 'return_on_equity', 'profitability.return_on_equity', 'ROE', 'percent', wiki.RETURN_ON_EQUITY_LINK),
    MetricSpec('profitability', 'return_on_assets', 'profitability.return_on_assets', 'ROA', 'percent', wiki.RETURN_ON_ASSETS_LINK),
    MetricSpec('profitability', 'roic', 'profitability.roic', 'ROIC', 'percent', wiki.ROIC_LINK),
    MetricSpec('profitability', 'roce', 'profitability.roce', 'ROCE', 'percent', wiki.ROCE_LINK),
    MetricSpec('profitability', 'return_on_equity_5y', 'profitability.return_on_equity_5y', 'Average ROE 5Y', 'percent', wiki.RETURN_ON_EQUITY_LINK),
    MetricSpec('profitability', 'return_on_equity_10y', 'profitability.return_on_equity_10y', 'Average ROE 10Y', 'percent', wiki.RETURN_ON_EQUITY_LINK),
    MetricSpec('profitability', 'gross_margin', 'profitability.gross_margin', 'Gross Margin', 'percent', wiki.GROSS_MARGIN_LINK),
    MetricSpec('profitability', 'gross_profit', 'profitability.gross_profit', 'Gross Profit', 'currency', wiki.GROSS_PROFIT_LINK),
    MetricSpec('profitability', 'ebitda', 'profitability.ebitda', 'EBITDA', 'currency', wiki.EBITDA_LINK),
    MetricSpec('profitability', 'ebitda_margin', 'profitability.ebitda_margin', 'EBITDA Margin', 'percent', wiki.EBITDA_MARGIN_LINK),
    MetricSpec('cash_flow', 'operating_cash_flow', 'cash_flow.operating_cash_flow', 'Operating Cash Flow', 'currency', wiki.OPERATING_CASH_FLOW_LINK),
    MetricSpec('cash_flow', 'capital_expenditures', 'cash_flow.capital_expenditures', 'Capital Expenditures', 'currency'),
    MetricSpec('cash_flow', 'fcf_margin', 'cash_flow.fcf_margin', 'FCF Margin', 'percent', wiki.FREE_CASH_FLOW_MARGIN_LINK),
    MetricSpec('cash_flow', 'cash_conversion', 'cash_flow.cash_conversion', 'Cash Conversion', 'multiple', wiki.CASH_CONVERSION_LINK),
    MetricSpec('cash_flow', 'operating_cash_flow_margin', 'cash_flow.operating_cash_flow_margin', 'OCF Margin', 'percent', wiki.OPERATING_CASH_FLOW_MARGIN_LINK),
    MetricSpec('cash_flow', 'owner_earnings', 'cash_flow.owner_earnings', 'Owner Earnings', 'currency', wiki.OWNER_EARNINGS_LINK),
    MetricSpec('cash_flow', 'owner_earnings_yield', 'cash_flow.owner_earnings_yield', 'Owner Earnings Yield', 'percent', wiki.OWNER_EARNINGS_YIELD_LINK),
    MetricSpec('financial_health', 'debt_to_equity', 'financial_health.debt_to_equity', 'Debt/Equity', 'number', wiki.DEBT_TO_EQUITY_LINK),
    MetricSpec('financial_health', 'current_ratio', 'financial_health.current_ratio', 'Current Ratio', 'number', wiki.CURRENT_RATIO_LINK),
    MetricSpec('financial_health', 'quick_ratio', 'financial_health.quick_ratio', 'Quick Ratio', 'number', wiki.QUICK_RATIO_LINK),
    MetricSpec('financial_health', 'free_cash_flow', 'financial_health.free_cash_flow', 'Free Cash Flow', 'currency', wiki.FREE_CASH_FLOW_LINK),
    MetricSpec('financial_health', 'net_debt', 'financial_health.net_debt', 'Net Debt', 'currency', wiki.NET_DEBT_LINK),
    MetricSpec('financial_health', 'net_debt_to_ebitda', 'financial_health.net_debt_to_ebitda', 'Net Debt/EBITDA', 'multiple', wiki.NET_DEBT_TO_EBITDA_LINK),
    MetricSpec('capital_allocation', 'shares_outstanding', 'capital_allocation.shares_outstanding', 'Shares Outstanding', 'integer', wiki.SHARES_OUTSTANDING_LINK),
    MetricSpec('capital_allocation', 'buyback_yield', 'capital_allocation.buyback_yield', 'Buyback Yield', 'percent', wiki.BUYBACK_YIELD_LINK),
    MetricSpec('capital_allocation', 'shareholder_yield', 'capital_allocation.shareholder_yield', 'Shareholder Yield', 'percent', wiki.SHAREHOLDER_YIELD_LINK),
    MetricSpec('capital_allocation', 'retained_earnings', 'capital_allocation.retained_earnings', 'Retained Earnings', 'currency', wiki.RETAINED_EARNINGS_LINK),
    MetricSpec('capital_allocation', 'acquisition_spending', 'capital_allocation.acquisition_spending', 'Acquisition Spending', 'currency', wiki.ACQUISITION_SPENDING_LINK),
    MetricSpec('working_capital', 'working_capital', 'working_capital.working_capital', 'Working Capital', 'currency', wiki.WORKING_CAPITAL_LINK),
    MetricSpec('working_capital', 'change_in_working_capital', 'working_capital.change_in_working_capital', 'Change in Working Capital', 'currency', wiki.CHANGE_IN_WORKING_CAPITAL_LINK),
    MetricSpec('working_capital', 'receivables', 'working_capital.receivables', 'Receivables', 'currency', wiki.RECEIVABLES_LINK),
    MetricSpec('working_capital', 'inventory', 'working_capital.inventory', 'Inventory', 'currency', wiki.INVENTORY_LINK),
    MetricSpec('working_capital', 'accounts_payable', 'working_capital.accounts_payable', 'Accounts Payable', 'currency', wiki.ACCOUNTS_PAYABLE_LINK),
)

SECTION_FALLBACKS: dict[str, str] = {
    'valuation': 'section.valuation',
    'profitability': 'section.profitability',
    'cash_flow': 'section.cash_flow',
    'growth': 'section.growth',
    'financial_health': 'section.financial_health',
    'capital_allocation': 'section.capital_allocation',
    'working_capital': 'section.working_capital',
    'prediction': 'section.prediction',
    'dividends_and_splits': 'section.dividends_and_splits',
    'recent_news': 'section.recent_news',
    'business_summary': 'section.business_summary',
    'report_context': 'section.report_context',
    'charts': 'section.charts',
}

PAGESIZES: dict[str, tuple[float, float]] = {   
    'letter': pagesizes.letter,
    'half_letter': pagesizes.HALF_LETTER,

    'a0': pagesizes.A0,
    'a1': pagesizes.A1, 'a2': pagesizes.A2, 'a3': pagesizes.A3,
    'a4': pagesizes.A4, 'a5': pagesizes.A5, 'a6': pagesizes.A6,

    'b0': pagesizes.B0,
    'b1': pagesizes.B1, 'b2': pagesizes.B2, 'b3': pagesizes.B3,
    'b4': pagesizes.B4, 'b5': pagesizes.B5, 'b6': pagesizes.B6,

    'c0': pagesizes.C0,
    'c1': pagesizes.C1, 'c2': pagesizes.C2, 'c3': pagesizes.C3,
    'c4': pagesizes.C4, 'c5': pagesizes.C5, 'c6': pagesizes.C6,

    'legal': pagesizes.legal,
    'tabloid': pagesizes.TABLOID,
    'ledger': pagesizes.LEDGER,
}



# ================================================== #
# HELPER FUNCTIONS                                   #
# ================================================== #

def _ui(report: Report, key: str, fallback: str | None = None) -> str:
    return ui_translate(
        report.account.language,
        key,
        fallback,
        throw_error=False,
    )


def _localized_date(report: Report, value: datetime) -> str:
    month: str = _ui(report, f'date.month.{value.month}', value.strftime('%b'))
    return f'{value.day:02d} {month} {value.year}'

def _localized_action(report: Report, action: str) -> str:
    return _ui(report, f'action.{action.lower()}', action.upper())

def _localized_period(report: Report, unit: str) -> str:
    return _ui(report, f'period.{unit.lower()}', unit)

# @lru_cache() -> implement first __hash__ for Report dtype
def _localized_quote_type(report: Report, value: object) -> str:
    text: str = _safe_text(value)
    normalized: str = ''.join(character for character in text.lower() if character.isalnum())
    aliases = {
        'equity': 'equity',
        'stock': 'stock',
        'etf': 'etf',
        'mutualfund': 'mutualfund',
        'fund': 'mutualfund',
        'reit': 'realestate',
        'realestate': 'realestate',
    }
    key: str = aliases.get(normalized, normalized)
    return _ui(report, f'quote_type.{key}', text)


def _translation(report: Report, mnemonic: str, fallback: str, field: str = 'title') -> str:
    language: Language = report.account.language
    snapshot: Translation = i18n(
        f'analyzer.{mnemonic}',
        language,
        throw_error=False,
    )('.', throw_error=False)

    return getattr(snapshot, field, None) or _ui(report, f'metric.{mnemonic}.{field}', fallback)


def _safe_text(value: object) -> str:
    if isinstance(value, Fact):
        value = value.value
    if value is None:
        return 'N/A'
    if isinstance(value, str) and value == '':
        return 'N/A'
    return str(value)

def _first_text(*values: object) -> str:
    for value in values:
        text: str = _safe_text(value)
        if text != 'N/A':
            return text
    return 'N/A'


def _color_hex(color: colors.Color) -> str:
    if isinstance(color, colors.Color):
        return color.hexval()

    if isinstance(color, dict):
        print(color)
        return colors.Color(
            color['r'],
            color['g'],
            color['b'],
        ).hexval()

    raise TypeError(f'Unsupported color type: {type(color)}')

def _grade_color(metric: Metric) -> colors.Color:
    return {
        MetricGrade.EXCELLENT: EXCELLENT_COLOR,
        MetricGrade.VERY_GOOD: VERY_GOOD_COLOR,
        MetricGrade.GOOD: GOOD_COLOR,
        MetricGrade.MEH: MEH_COLOR,
        MetricGrade.BAD: BAD_COLOR,
        MetricGrade.VERY_BAD: VERY_BAD_COLOR,
        MetricGrade.AWFUL: AWFUL_COLOR,
    }.get(metric.grade, NEUTRAL_COLOR)


def _format_metric(metric: Metric, kind: MetricKind) -> str:
    if metric.unavailable:
        return 'Unavailable'
    if metric.value is None or metric.is_nan:
        return 'N/A'

    value: object = metric.value
    match kind:
        case 'currency':
            if not isinstance(value, Money):
                return f'{float(value):,.2f}'
            n = value.format('.2f-pretty:formal')
            print(f'{metric} metric: {n}')
            return n
        case 'percent':
            if isinstance(value, Percentage):
                return float(value)
            return float(Percentage.from_fraction(value))
        case 'multiple':
            return f'{float(value):,.2f}x'
        case 'integer':
            return f'{int(float(value)):,}'
        case _:
            return f'{float(value):,.2f}'

def _format_delta(report: Report, metric: Metric) -> str:
    if metric.delta_pct is None:
        return _ui(report, 'summary.change_unavailable', 'Change unavailable')
    delta = float(metric.delta_pct)
    sign = '+' if delta > 0 else ''
    return f'{sign}{delta:.3f}% {_ui(report, "summary.vs_prior_period", "vs. prior period")}'

def _format_fact(value: Fact, kind: MetricKind = 'number') -> str:
    if value.value is None:
        return 'N/A'
    if kind == 'currency' and isinstance(value.value, Money):
        return value.value.currency.format_amount(value.value.value, 'formal', 2)
    if kind == 'integer':
        return f'{int(float(value.value)):,}'
    return f'{float(value.value):,.2f}'


def _metric_status_text(report: Report, metric: Metric) -> str:
    fallbacks = {
        MetricStatus.OK: 'Calculated correctly',
        MetricStatus.NA: 'Not applicable',
        MetricStatus.NaN: 'Invalid number',
        MetricStatus.NOT_AVAILABLE: 'Not available for this security',
        MetricStatus.NOT_RATED: 'Could not be rated',
    }
    if metric.status == MetricStatus.OK:
        return metric.label or (
            metric.grade.value.replace('_', ' ').title()
            if metric.grade
            else _ui(
                report,
                f'metric_status.{MetricStatus.OK.value}',
                fallbacks[MetricStatus.OK],
            )
        )
    return _ui(
        report,
        f'metric_status.{metric.status.value}',
        fallbacks[metric.status],
    )


def _requested(report: Report, section: str, field: str) -> bool:
    if report.mode.value != 'custom':
        return True

    requested: set[str] = {item.strip().lower() for item in report.custom_report}
    aliases: set[str] = {field.lower()}
    if field == 'ev_to_market_cap':
        aliases.add('ev2market_cap')
    return (
        section.lower() in requested
        or field.lower() in requested
        or bool(aliases.intersection(requested))
    )

def _paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def _metric_card(
    report: Report,
    spec: MetricSpec,
    metric: Metric,
    width: float,
    styles: dict[str, ParagraphStyle],
) -> Table:
    title: str = _translation(report, spec.mnemonic, spec.fallback)
    label: str = escape(title)
    if spec.link:
        label = f'<link href="{escape(spec.link)}" color="{_color_hex(LINK_COLOR)}">{label}</link>'

    value_color: Color = _grade_color(metric)
    rating: str = _metric_status_text(report, metric)
    content: list[Flowable] = [
        _paragraph(label, styles['metric_label']),
        Spacer(1, 5),
        _paragraph(
            f'<font color="{_color_hex(value_color)}"><b>{escape(str(_format_metric(metric, spec.kind)))}</b></font>',
            styles['metric_value'],
        ),
        Spacer(1, 3),
        _paragraph(escape(rating), styles['metric_rating']),
    ]
    card: Table = Table([[content]], colWidths=[width])
    card.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CARD_COLOR),
        ('BOX', (0, 0), (-1, -1), 0.5, RULE_COLOR),
        ('LINEBEFORE', (0, 0), (0, -1), 3, value_color),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    return card

def _metric_grid(
    report: Report,
    specs: list[MetricSpec],
    section: object,
    width: float,
    styles: dict[str, ParagraphStyle],
) -> Table | None:
    visible_specs: list[MetricSpec] = [
        spec for spec in specs
        if _requested(report, spec.section, spec.field)
    ]
    if not visible_specs:
        return None

    column_width: float = width / 3
    rows: list[list[Table | str]] = []
    for offset in range(0, len(visible_specs), 3):
        row: list[Table | str] = []
        for spec in visible_specs[offset:offset + 3]:
            metric = getattr(section, spec.field)
            row.append(_metric_card(report, spec, metric, column_width - 8, styles))
        row.extend([''] * (3 - len(row)))
        rows.append(row)

    grid: Table = Table(rows, colWidths=[column_width] * 3, hAlign='LEFT')
    grid.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    return grid


def _section_header(
    report: Report,
    section: str,
    styles: dict[str, ParagraphStyle],
) -> Table:
    fallback_key: str = SECTION_FALLBACKS[section]
    title: str = _translation(report, section, _ui(report, fallback_key, section))
    description: str = _translation(report, section, '', field='description')
    title_block: list[Flowable] = [
        _paragraph(escape(title), styles['section']),
        _paragraph(escape(description), styles['section_description']),
    ]
    header: Table = Table([['', title_block]], colWidths=[5, None])
    header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), ACCENT_COLOR),
        ('BACKGROUND', (1, 0), (1, 0), SURFACE_COLOR),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), 0),
        ('LEFTPADDING', (1, 0), (1, 0), 12),
        ('RIGHTPADDING', (1, 0), (1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return header


class _CoverPage(Flowable):
    def __init__(
        self,
        report: Report,
        styles: dict[str, ParagraphStyle],
        page_width: float,
        page_height: float,
        left_margin: float,
        bottom_margin: float,
        generated_at: datetime,
    ) -> None:
        super().__init__()
        self.report: Report = report
        self.styles: dict[str, ParagraphStyle] = styles
        self.page_width: float = page_width
        self.page_height: float = page_height
        self.left_margin: float = left_margin
        self.bottom_margin: float = bottom_margin
        self.generated_at: datetime = generated_at

    def wrap(self, avail_width: float, avail_height: float) -> tuple[float, float]:
        return avail_width, avail_height

    def draw(self) -> None:
        canvas: Canvas = self.canv
        x0: float = -self.left_margin
        y0: float = -self.bottom_margin
        ticker: Ticker = self.report.ticker
        descriptive: DescriptiveFacts = self.report.analysis.descriptive_facts
        price: Metric = self.report.analysis.quantifiable_facts.price
        price_text: str = _format_metric(price, 'currency')
        delta_text: str = _format_delta(self.report, price)
        delta_color: Color = GAIN_COLOR if price.delta_pct is None or float(price.delta_pct) >= 0 else NEGATIVE_COLOR

        canvas.saveState()
        # background: full page
        canvas.setFillColor(PAGE_BACKGROUND)
        canvas.rect(x0 - 6, y0 - 6, self.page_width, self.page_height, stroke=0, fill=1)
        # line: top left
        canvas.setFillColor(ACCENT_COLOR)
        canvas.rect(x0 + 52, y0 + self.page_height - 90, 156, 5, stroke=0, fill=1)
        canvas.setStrokeColor(COVER_LINE_COLOR)
        canvas.setLineWidth(0.7)
        canvas.line(x0 + 52, y0 + 54, x0 + self.page_width - 52, y0 + 54)
        # title: top right
        canvas.setFillColor(COVER_MUTED_COLOR)
        canvas.setFont(Theme.FONT_HEADER, 11)
        canvas.drawRightString(
            x0 + self.page_width - 52,
            y0 + self.page_height - 90,
            _ui(self.report, APP_NAME),
        )

        # ticker: below {line}, left
        ticker_para: Paragraph = Paragraph(escape(ticker.symbol), self.styles['cover_ticker'])
        ticker_para.wrapOn(canvas, self.page_width - 104, 60)
        ticker_para.drawOn(canvas, x0 + 52, y0 + self.page_height - 180)

        # company: below {ticker}, left
        company_para: Paragraph = Paragraph(escape(_first_text(descriptive.formal_name, descriptive.name)), self.styles['cover_company'])
        company_para.wrapOn(canvas, self.page_width - 104, 70)
        company_para.drawOn(canvas, x0 + 52, y0 + self.page_height - 238)

        # price: mid right
        canvas.setFillColor(WHITE_COLOR)
        canvas.setFont(Theme.FONT_COVER_PRICE, 30)
        canvas.drawRightString(x0 + self.page_width - 52, y0 + self.page_height - 342, price_text)
        # delta: below {price}, mid right
        canvas.setFillColor(delta_color)
        canvas.setFont(Theme.FONT_HEADER, 13)
        canvas.drawRightString(x0 + self.page_width - 52, y0 + self.page_height - 366, delta_text)

        # metadata: above {links}, bottom-left
        canvas.setFillColor(COVER_MUTED_COLOR)
        canvas.setFont(Theme.FONT_HEADER, 14)
        canvas.drawString(x0 + 52, y0 + 112, f'{_ui(self.report, "cover.region_label")}: {ticker.region}  |  {_ui(self.report, "cover.ticker_label")}: {ticker.ticker}')
        # links: bottom-left
        canvas.setFont(Theme.FONT_HEADER, 12)
        canvas.drawString(
            x0 + 52,
            y0 + 84,
            f'{_ui(self.report, "cover.gbm", "GBM")}  |  '
            f'{_ui(self.report, "cover.tradingview", "TradingView")}',
        )
        canvas.setFont(Theme.FONT_COVER_META, 10)
        canvas.drawRightString(
            x0 + self.page_width - 52,
            y0 + 84,
            f'{_ui(self.report, "cover.report_date", "Report date")}: '
            f'{_localized_date(self.report, self.generated_at)}',
        )

        canvas.linkURL(
            Theme.GBM_URL.format(symbol=ticker.symbol),
            (x0 + 52, y0 + 76, x0 + 220, y0 + 96),
            relative=0,
        )
        canvas.linkURL(
            Theme.TRADINGVIEW_URL.format(symbol=ticker.symbol),
            (x0 + 220, y0 + 76, x0 + 390, y0 + 96),
            relative=0,
        )
        canvas.restoreState()


def _draw_footer_text(canvas, doc: SimpleDocTemplate, report: Report) -> None:
    page_width, _ = pagesizes.letter
    canvas.setFillColor(MUTED_COLOR)
    canvas.setFont(Theme.FONT_FOOTER, 7.5)
    canvas.drawString(
        doc.leftMargin,
        20,
        _ui(
            report,
            'footer.generated_by',
            'Report generated by {app} ~ {author}',
        ).format(app=APP_NAME_CODING, author=APP_AUTHOR),
    )
    canvas.drawRightString(
        page_width - doc.rightMargin,
        20,
        _ui(report, 'footer.page', 'Page {page}').format(page=doc.page),
    )

def _draw_later_page(canvas, doc: SimpleDocTemplate, report: Report) -> None:
    page_width, page_height = pagesizes.letter
    canvas.saveState()
    canvas.setStrokeColor(RULE_COLOR)
    canvas.setLineWidth(0.6)
    canvas.line(doc.leftMargin, page_height - 34, page_width - doc.rightMargin, page_height - 34)
    canvas.setFillColor(MUTED_COLOR)
    canvas.setFont(Theme.FONT_HEADER, 8)
    canvas.drawString(doc.leftMargin, page_height - 25, report.ticker.symbol)
    canvas.setFont(Theme.FONT_FOOTER, 7.5)
    ticker_type: str = _localized_quote_type(
        report,
        report.analysis.descriptive_facts.quote_type,
    )
    canvas.drawRightString(
        page_width - doc.rightMargin,
        page_height - 25,
        f'{_ui(report, APP_NAME)} · {ticker_type.upper()}',
    )
    canvas.line(doc.leftMargin, 31, page_width - doc.rightMargin, 31)
    _draw_footer_text(canvas, doc, report)
    canvas.restoreState()



# ================================================== #
# PDF RENDERER                                       #
# ================================================== #

class PDFRenderer:
    def __init__(self, *args: Any, **kwargs: dict[str, Any]) -> None:
        self.args: tuple[Any, ...] = args
        self.kwargs: dict[str, Any] = kwargs

        self.__pagesize: str = self.kwargs.get('pagesize', 'letter').lower()
        self.__page_width, self.__page_height = PAGESIZES.get(self.__pagesize, pagesizes.letter)

    def normalize_output(self, report: Report, output: str | None = None) -> Path:
        destination: str | None = normalize_output(output, report, 'pdf')
        root: Path = Path(destination or f'report_{report.ticker.symbol.upper()}--{datetime.now().strftime("%Y-%m-%d")}.pdf')
        root.parent.mkdir(parents=True, exist_ok=True)
        return root

    def render(self, report: Report, output: str | None = None) -> None:
        root: Path = self.normalize_output(report, output)
        root.parent.mkdir(parents=True, exist_ok=True)
        left_margin = 46
        right_margin = 46
        top_margin = 52
        bottom_margin = 45
        styles: dict[str, ParagraphStyle] = build_styles()
        generated_at = datetime.now()
        doc: SimpleDocTemplate = SimpleDocTemplate(
            str(root),
            pagesize=(self.__page_width, self.__page_height),
            leftMargin=left_margin,
            rightMargin=right_margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
            title=_ui(
                report,
                'document.title',
                '{symbol}',
            ).format(symbol=report.ticker.symbol),
            author=APP_NAME_CODING,
            subject=_ui(
                report,
                'document.subject',
                'Fundamental stock analysis report',
            ),
            application=APP_NAME_CODING,
            keywords=_ui(
                report,
                'document.keywords',
                ', '.join(get_preset(report.mode).sections),
            )
        )

        story: list[Flowable] = [
            _CoverPage(
                report,
                styles,
                self.__page_width,
                self.__page_height,
                left_margin,
                bottom_margin,
                generated_at,
            ),
            PageBreak(),
        ]
        story.extend(self._summary(report, styles, doc.width))

        preset: ReportPreset = get_preset(report.mode)
        if preset.show_explanation and self._feature_requested(report, 'explanation'):
            story.extend(self._prediction(report, styles, doc.width))
        if preset.show_analysis:
            analysis: list[Flowable] = self._analysis(report, preset, styles, doc.width)
            story.extend(
                [
                    PageBreak(),
                    *analysis
                ] if not preset.show_explanation else analysis
            )
        if preset.show_facts and self._feature_requested(report, 'dividends_and_splits'):
            story.extend(self._dividends_and_splits(report, styles, doc.width))
        if preset.show_news:
            story.extend(n := self._news(report, styles, doc.width))
        if report.charts and self._feature_requested(report, 'charts'):
            chart_story = self._charts(report, styles, doc.width)
            if chart_story:
                story.extend([PageBreak(), *chart_story])
            
            story.extend([
                PageBreak(),
                *self._context_page(report, styles, doc.width, generated_at),
            ])

        doc.build(
            story,
            onFirstPage=lambda canvas, document: _draw_footer_text(canvas, document, report),
            onLaterPages=lambda canvas, document: _draw_later_page(canvas, document, report),
        )

    @staticmethod
    def _feature_requested(report: Report, feature: str) -> bool:
        if report.mode.value != 'custom':
            return True
        requested: set[str] = {item.strip().lower() for item in report.custom_report}
        if feature == 'dividends_and_splits':
            return bool(requested.intersection({'dividends_and_splits', 'dividends', 'splits'}))
        return feature in requested

    @staticmethod
    def _context_page(
        report: Report,
        styles: dict[str, ParagraphStyle],
        width: float,
        generated_at: datetime,
    ) -> list[Flowable]:
        descriptive: DescriptiveFacts = report.analysis.descriptive_facts
        quote_type: str = _localized_quote_type(report, descriptive.quote_type)
        company: str = _first_text(descriptive.formal_name, descriptive.name)
        values: dict[str, str] = {
            'app': _ui(report, APP_NAME),
            'author': APP_AUTHOR,
            'quote_type': quote_type,
            'symbol': report.ticker.ticker,
            'company': company,
            'date': _localized_date(report, generated_at),
            'time': generated_at.strftime('%H:%M'),
        }

        def prose(key: str, fallback: str) -> Paragraph:
            text: str = _ui(report, key, fallback).format(
                **{name: escape(value) for name, value in values.items()},
            )
            return _paragraph(text, styles['body'])

        paragraphs: list[Paragraph] = [
            prose(
                'context.about_app',
                '{app} is a financial research application created by {author}.',
            ),
            prose(
                'context.report_scope',
                'This report covers {quote_type} {symbol}, {company}, and was generated on {date} at {time}.',
            ),
            prose(
                'context.explains',
                'The report explains the available market and fundamental indicators.',
            ),
            prose(
                'context.disclaimer',
                'The information provided in this report is for informational purposes only and should not be considered as financial advice. '
                'Investing in securities involves risks, and individuals should conduct their own research or consult with a qualified financial advisor before making investment decisions.',
            )
        ]
        context_card: Table = Table([[paragraphs]], colWidths=[width])
        context_card.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), CARD_COLOR),
            ('BOX', (0, 0), (-1, -1), 0.5, RULE_COLOR),
            ('LEFTPADDING', (0, 0), (-1, -1), 18),
            ('RIGHTPADDING', (0, 0), (-1, -1), 18),
            ('TOPPADDING', (0, 0), (-1, -1), 18),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 18),
        ]))
        return [
            _paragraph(
                escape(_ui(report, 'context.eyebrow', 'ABOUT THIS REPORT')),
                styles['eyebrow'],
            ),
            _paragraph(
                paragraphs[0].getPlainText(),
                styles.get('body_muted_justified', styles['body_muted']),
            ),
            Spacer(1, 5),
            _paragraph(
                paragraphs[1].getPlainText(),
                styles.get('body_muted_justified', styles['body_muted']),
            ),
            Spacer(1, 5),
            _paragraph(
                paragraphs[2].getPlainText(),
                styles.get('body_muted_justified', styles['body_muted']),
            ),
            Spacer(1, 5),
            _paragraph(
                paragraphs[3].getPlainText(),
                styles.get('body_muted_justified', styles['body_muted']),
            ),
            Spacer(1, 15),
            _paragraph(
                _ui(report, 'context.license', LICENSE),
                styles['eyebrow'],
            ),
            _paragraph(
                LICENSE_TEXT,
                styles['preformatted'],
            ),
        ]

    @staticmethod
    def _summary(
        report: Report,
        styles: dict[str, ParagraphStyle],
        width: float,
    ) -> list[Flowable]:
        descriptive = report.analysis.descriptive_facts
        quantifiable: QuantifiableFacts = report.analysis.quantifiable_facts
        title = _first_text(descriptive.formal_name, descriptive.name)
        cards = [
            (
                _ui(report, 'summary.open', 'OPEN'),
                _format_fact(descriptive.open, 'currency'),
                _ui(report, 'summary.open_context', 'Session open'),
            ),
            (
                _ui(report, 'summary.high', 'HIGH'),
                _format_fact(descriptive.high, 'currency'),
                _ui(report, 'summary.high_context', 'Session high'),
            ),
            (
                _ui(report, 'summary.low', 'LOW'),
                _format_fact(descriptive.low, 'currency'),
                _ui(report, 'summary.low_context', 'Session low'),
            ),
            (
                _ui(report, 'summary.close', 'CLOSE'),
                _format_fact(descriptive.close, 'currency'),
                _ui(report, 'summary.close_context', 'Latest close'),
            ),
        ]
        card_width = width / 4
        card_tables: list[Table] = []
        for label, value, note in cards:
            card = Table([[
                [
                    _paragraph(escape(label.upper()), styles['card_label']),
                    Spacer(1, 5),
                    _paragraph(escape(value), styles['card_value']),
                    Spacer(1, 3),
                    _paragraph(escape(note), styles['card_note']),
                ],
            ]], colWidths=[card_width - 8])
            card.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), CARD_COLOR),
                ('BOX', (0, 0), (-1, -1), 0.5, RULE_COLOR),
                ('LEFTPADDING', (0, 0), (-1, -1), 9),
                ('RIGHTPADDING', (0, 0), (-1, -1), 9),
                ('TOPPADDING', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
            ]))
            card_tables.append(card)
        cards_grid = Table([card_tables], colWidths=[card_width] * 4)
        cards_grid.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        website_safed: str = escape(_safe_text(descriptive.website))
        website_cell: Paragraph = (
            Paragraph(
                f'<link href="{website_safed}">'
                f'<font color="{LINK_COLOR}"><u>{website_safed}</u></font>'
                f'</link>',
                styles['body'],
            )
            if website_safed not in ('', 'N/A')
            else website_safed
        )
        details = [
            [
                _ui(report, 'details.company', 'Company'),
                title,
                _ui(report, 'details.ticker', 'Ticker'),
                report.ticker.ticker,
            ],
            [
                _ui(report, 'details.region', 'Region'),
                report.ticker.region,
                _ui(report, 'details.currency', 'Currency'),
                _safe_text(descriptive.currency),
            ],
            [
                _ui(report, 'details.sector', 'Sector'),
                _safe_text(descriptive.sector),
                _ui(report, 'details.industry', 'Industry'),
                _safe_text(descriptive.industry),
            ],
            [
                _ui(report, 'details.address', 'Address'),
                _safe_text(descriptive.address),
                _ui(report, 'details.quote_type', 'Quote type'),
                _localized_quote_type(report, descriptive.quote_type),
            ],
            [
                _ui(report, 'details.website', 'Website'),
                website_cell,
                _ui(report, 'details.phone', 'Phone'),
                _safe_text(descriptive.phone),
            ],
        ]
        details_table = Table(details, colWidths=[width * 0.15, width * 0.35, width * 0.15, width * 0.35])
        details_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), CARD_COLOR),
            ('BOX', (0, 0), (-1, -1), 0.5, RULE_COLOR),
            ('INNERGRID', (0, 0), (-1, -1), 0.35, RULE_COLOR),
            ('FONTNAME', (0, 0), (-1, -1), Theme.FONT_BODY),
            ('TEXTCOLOR', (0, 0), (-1, -1), INK_COLOR),
            ('FONTNAME', (0, 0), (0, -1), Theme.FONT_TITLE),
            ('FONTNAME', (2, 0), (2, -1), Theme.FONT_TITLE),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        return [
            _paragraph(
                escape(_ui(report, 'summary.eyebrow', 'INVESTMENT BRIEF')),
                styles['eyebrow'],
            ),
            _paragraph(escape(title), styles['title']),
            _paragraph(
                escape(_safe_text(descriptive.description)),
                styles['body_muted'],
            ),
            Spacer(1, 13),
            cards_grid,
            Spacer(1, 17),
            _paragraph(
                escape(_ui(report, 'summary.company_profile', 'Company profile')),
                styles['section'],
            ),
            Spacer(1, 7),
            details_table,
            Spacer(1, 22),
        ]

    @staticmethod
    def _prediction(
        report: Report,
        styles: dict[str, ParagraphStyle],
        width: float,
    ) -> list[Flowable]:
        prediction: PredictionResult = report.prediction_result
        explanation: Explanation | None = report.explanation
        action_value = prediction.top_action.value
        action = _localized_action(report, action_value)
        action_color = (
            GAIN_COLOR
            if action_value == 'buy'
            else NEGATIVE_COLOR
            if action_value == 'sell'
            else NEUTRAL_COLOR
        )
        probability_rows = [
            [
                _paragraph(
                    escape(_localized_action(report, possible.action.value)),
                    styles['table_value'],
                ),
                _paragraph(
                    f'<font color="{_color_hex(action_color)}"><b>{possible.probability:.2f}</b></font>',
                    styles['prediction_probability'],
                ),
            ]
            for possible in prediction.action_probabilities
        ]
        prediction_table = Table([
            [
                [
                    _paragraph(
                        _ui(report, 'prediction.model_signal', 'MODEL SIGNAL'),
                        styles['eyebrow'],
                    ),
                    Spacer(1, 5),
                    _paragraph(
                        f'<font color="{_color_hex(action_color)}">{escape(action)}</font>',
                        styles['prediction_action'],
                    ),
                    _paragraph(
                        f'{escape(_ui(report, "prediction.confidence", "Confidence"))}: '
                        f'{prediction.confidence:.2f}  |  '
                        f'{escape(_ui(report, "prediction.horizon", "Horizon"))}: '
                        f'{prediction.horizon} '
                        f'{escape(_localized_period(report, prediction.horizon_unit))}',
                        styles['body_muted'],
                    ),
                ],
                Table(
                    probability_rows or [[
                        _paragraph('N/A', styles['table_value']),
                        _paragraph('N/A', styles['prediction_probability']),
                    ]],
                    colWidths=[width * 0.12, width * 0.16],
                ),
            ],
        ], colWidths=[width * 0.68, width * 0.32])
        prediction_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), CARD_COLOR),
            ('BOX', (0, 0), (-1, -1), 0.5, RULE_COLOR),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        story: list[ListItem] = [
            _section_header(report, 'prediction', styles),
            Spacer(1, 8),
            prediction_table,
        ]
        if explanation:
            story.extend([
                Spacer(1, 10),
                _paragraph(escape(explanation.summary), styles['body']),
            ])
            point_color: dict[Reasoning, str] = {
                Reasoning.POSITIVE: GAIN_COLOR,
                Reasoning.NEGATIVE: NEGATIVE_COLOR,
                Reasoning.NEUTRAL: NEUTRAL_COLOR,
            }
            story.extend([
                _paragraph(
                    (
                        f'<font color="{_color_hex(point_color.get(point.reasoning, Reasoning.NEUTRAL))}">'
                        f'<b>{point.reasoning.value}</b>'
                        f'</font>'
                    ) + ' ' + escape(point.content), styles['body']
                ) for point in explanation.points
            ])

        story.append(Spacer(1, 18))
        return story

    @staticmethod
    def _analysis(
        report: Report,
        preset: ReportPreset,
        styles: dict[str, ParagraphStyle],
        width: float,
    ) -> list[Flowable]:
        story: list[Flowable] = []
        sections: list[tuple[str, object]] = [
            ('valuation', report.analysis.valuation),
            ('profitability', report.analysis.profitability),
            ('cash_flow', report.analysis.cash_flow),
            ('growth', report.analysis.growth),
            ('financial_health', report.analysis.financial_health),
            ('capital_allocation', report.analysis.capital_allocation),
            ('working_capital', report.analysis.working_capital),
        ]
        for section_name, section_model in sections:
            if section_name not in preset.sections:
                continue

            section_specs: list[MetricSpec] = [spec for spec in METRIC_SPECS if spec.section == section_name]
            grid: Table | None = _metric_grid(report, section_specs, section_model, width, styles)
            if grid is None:
                continue

            story.extend([
                _section_header(report, section_name, styles),
                Spacer(1, 8),
                grid,
                Spacer(1, 17),
            ])

        return story

    @staticmethod
    def _dividends_and_splits(
        report: Report,
        styles: dict[str, ParagraphStyle],
        width: float,
    ) -> list[Flowable]:
        quantitative: QuantifiableFacts = report.analysis.quantifiable_facts
        descriptive: DescriptiveFacts = report.analysis.descriptive_facts

        def _safe_split(text: str) -> str:
            if descriptive.splits.value is None or text.strip() == '':
                return 'N/A'

            text: str = text.format(
                count=descriptive.splits.value.split(' on ')[0],
                split_date=descriptive.splits.value.split(' on ')[1],
            )
            return text

        rows: list[list[Any]] = [
            [
                _ui(report, 'facts.dividend_yield', 'Dividend yield'),
                _format_metric(quantitative.dividend_yield, 'percent'),
            ],
            [
                _ui(report, 'facts.dividend_rate', 'Dividend rate'),
                _format_metric(quantitative.dividend_rate, 'currency'),
            ],
            [
                _ui(report, 'facts.last_dividend', 'Last dividend'),
                _safe_text(descriptive.last_dividend),
            ],
            [
                _ui(report, 'facts.splits', 'Splits'),
                # E.g. "4.0 on 2023-06-15"
                _safe_split(_ui(report, 'dividends_and_splits.split_format', '{count:0f} splits on {split_date}')),
            ],
        ]
        table: Table = Table(rows, colWidths=[width * 0.38, width * 0.62])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), CARD_COLOR),
            ('BOX', (0, 0), (-1, -1), 0.5, RULE_COLOR),
            ('INNERGRID', (0, 0), (-1, -1), 0.35, RULE_COLOR),
            ('FONTNAME', (0, 0), (0, -1), Theme.FONT_TITLE),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('TEXTCOLOR', (0, 0), (-1, -1), INK_COLOR),
            ('LEFTPADDING', (0, 0), (-1, -1), 9),
            ('RIGHTPADDING', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ]))
        return [
            _section_header(report, 'dividends_and_splits', styles),
            Spacer(1, 8),
            table,
            Spacer(1, 18),
        ]

    @staticmethod
    def _news(
        report: Report,
        styles: dict[str, ParagraphStyle],
        width: float,
    ) -> list[Flowable]:
        news = list(report.news_compilation)
        content: Paragraph = _paragraph(
            _ui(report, 'news.empty', 'No recent news available.'),
            styles['body_muted'],
        )
        story: list[Flowable] = [
            _section_header(report, 'recent_news', styles),
            Spacer(1, 8)
        ]

        if news:
            content: ListFlowable = ListFlowable(
                flowables=[
                    ListItem(
                        _paragraph(
                            item.summary + f' ({datetime.fromisoformat(item.published_at).strftime("%Y-%m-%d %H:%M:%S")} UTC)',
                            styles['body_justified']
                        )
                    ) for item in news
                ],
                start='1',
                bulletType='1',
                leftIndent=20,
                bulletFontName=Theme.FONT_BODY,
            )
        
        story.append(content)
        story.append(Spacer(1, 18))
        return story

    @staticmethod
    def _chart_requested(report: Report, chart_name: str) -> bool:
        base_chart_name = chart_name
        if chart_name.startswith('price_history_'):
            base_chart_name = 'price_history'
        elif chart_name.startswith('drawdown_'):
            base_chart_name = 'drawdown'
        if report.mode.value != 'custom':
            preset_graphs: dict[str, set[str]] = {
                'info': {'price_history'},
                'growth': {
                    'price_history',
                    'drawdown',
                    'fundamental_growth',
                    'fair_value',
                },
                'validation': {
                    'price_history',
                    'drawdown',
                    'valuation_history',
                    'fair_value',
                },
                'classic': {
                    'price_history',
                    'relative_performance',
                    'drawdown',
                    'fair_value',
                    'valuation_history',
                    'fundamental_growth',
                    'dividends_history',
                    'fundamental_value',
                },
                'full': {
                    'price_history',
                    'relative_performance',
                    'drawdown',
                    'fair_value',
                    'valuation_history',
                    'fundamental_growth',
                    'dividends_history',
                    'fundamental_value',
                },
            }
            return base_chart_name in preset_graphs.get(report.mode.value, set())

        requested = {item.strip().lower() for item in report.custom_report}
        aliases: dict[str, set[str]] = {
            'price_history': {'price_history', 'price', 'close'},
            'relative_performance': {'relative_performance'},
            'drawdown': {'drawdown'},
            'fair_value': {'fair_value', 'fundamental_value'},
            'valuation_history': {
                'valuation_history',
                'valuation',
                'pe_ratio',
                'peg_ratio',
                'price_to_fcf',
                'ev_to_ebitda',
                'price_to_sales',
            },
            'fundamental_growth': {
                'fundamental_growth',
                'growth',
                'revenue_growth',
                'earnings_growth',
                'eps_growth',
                'fcf_growth',
            },
            'dividends_history': {
                'dividends_history',
                'dividends',
                'dividend_rate',
                'dividend_yield',
            },
            'fundamental_value': {'fundamental_value', 'fair_value'},
        }
        return bool(requested.intersection(aliases.get(base_chart_name, {base_chart_name})))

    @staticmethod
    def _history_points(
        report: Report,
        period: str = '10y',
    ) -> list[YFinanceHistoryPoint]:
        if period == '10y':
            history_fact = report.analysis.history_10y_1mo.price.value
            if not history_fact:
                history_fact = report.analysis.descriptive_facts.history_10y_1mo.value
        else:
            field_name = {
                '5y': 'history_5y_1d',
                '1y': 'history_1y_1d',
                '3mo': 'history_3mo_1d',
                '1w': 'history_1w_1d',
            }.get(period)
            history_fact = (
                getattr(report.analysis.descriptive_facts, field_name).value
                if field_name
                else []
            )

        if not isinstance(history_fact, list):
            return []
        
        return [
            point for point in history_fact
            if isinstance(point, YFinanceHistoryPoint)
            and point.close is not None
        ]

    @staticmethod
    def _sp500_points(report: Report) -> list[YFinanceHistoryPoint]:
        value = report.analysis.history_10y_1mo.sp500.value
        if not isinstance(value, list):
            return []
        
        return [
            point for point in value
            if isinstance(point, YFinanceHistoryPoint)
            and point.close is not None
        ]

    @staticmethod
    def _metric_points(fact: Fact) -> list[HistoricalMetricPoint]:
        if not isinstance(fact.value, list):
            return []
        
        return [
            point for point in fact.value
            if isinstance(point, HistoricalMetricPoint)
            and point.value is not None
        ]

    @staticmethod
    def _indexed(values: list[float]) -> list[tuple[int, float]]:
        if not values:
            return []

        baseline: float = values[0]
        if baseline == 0:
            return []

        return [
            (index, value / baseline * 100)
            for index, value in enumerate(values)
        ]

    @staticmethod
    def _moving_average(values: list[float], window: int) -> list[tuple[int, float]]:
        if len(values) < window:
            return []
    
        return [
            (
                index,
                sum(values[index - window + 1:index + 1]) / window,
            )
            for index in range(window - 1, len(values))
        ]

    @staticmethod
    def _chart_drawing(
        report: Report,
        chart_name: str,
        series: list[ChartSeries],
        dates: list[date],
        width: float,
        *,
        note: str | None = None,
    ) -> Drawing | None:
        series: list[tuple[int, float]] = [item for item in series if item.values]
        if not series:
            return None

        drawing_width: float = min(width, 500)
        drawing_height: int = 238
        drawing: Drawing = Drawing(drawing_width, drawing_height)
        drawing.add(Rect(
            0,
            0,
            drawing_width,
            drawing_height,
            fillColor=CARD_COLOR,
            strokeColor=RULE_COLOR,
            strokeWidth=0.5,
            rx=8,
            ry=8,
        ))
        title: str = _ui(report, f'chart.{chart_name}', chart_name.replace('_', ' ').title())
        description: str = _ui(report, f'chart.{chart_name}_description', '')
        drawing.add(String(
            18,
            212,
            title,
            fontName=Theme.FONT_TITLE,
            fontSize=11,
            fillColor=INK_COLOR,
        ))
        drawing.add(String(
            18,
            198,
            description,
            fontName=Theme.FONT_BODY,
            fontSize=7.5,
            fillColor=MUTED_COLOR,
        ))

        plot: LinePlot = LinePlot()
        plot.x = 42
        plot.y = 52
        plot.width = drawing_width - 64
        plot.height = 122
        plot.data = [item.values for item in series]
        plot.joinedLines = True
        plot.xValueAxis.strokeColor = CHART_GRID_COLOR
        plot.xValueAxis.strokeWidth = 0.4
        plot.xValueAxis.visibleGrid = True
        plot.xValueAxis.gridStrokeColor = CHART_GRID_COLOR
        plot.xValueAxis.gridStrokeWidth = 0.35
        plot.yValueAxis.strokeColor = CHART_GRID_COLOR
        plot.yValueAxis.strokeWidth = 0.4
        plot.yValueAxis.visibleGrid = True
        plot.yValueAxis.gridStrokeColor = CHART_GRID_COLOR
        plot.yValueAxis.gridStrokeWidth = 0.35
        all_values: list[float] = [
            value
            for item in series
            for _, value in item.values
        ]
        minimum: float = min(all_values)
        maximum: float = max(all_values)
        padding: float = (maximum - minimum) * 0.08 or max(abs(maximum) * 0.05, 1)
        plot.xValueAxis.valueMin = 0
        last_x: int = max(
            max(index for item in series for index, _ in item.values),
            1,
        )
        plot.xValueAxis.valueMax = last_x
        plot.xValueAxis.valueStep = max(1, ceil(last_x / 4))
        plot.yValueAxis.valueMin = minimum - padding
        plot.yValueAxis.valueMax = maximum + padding
        span_days: int = (dates[-1] - dates[0]).days if len(dates) > 1 else 0
        date_format: str = (
            '%Y'
            if span_days > 5 * 365
            else '%b %Y'
            if span_days > 90
            else '%d %b'
        )
        plot.xValueAxis.labelTextFormat = lambda value: (
            dates[min(max(int(round(value)), 0), len(dates) - 1)].strftime(date_format)
            if dates else str(int(value))
        )
        for index, item in enumerate(series):
            plot.lines[index].strokeColor = item.color
            plot.lines[index].strokeWidth = 1.8
        drawing.add(plot)

        legend_x: float = 42
        legend_y: float = 18
        legend_font_size: float = 7
        for item in series:
            label_width = stringWidth(
                item.name,
                Theme.FONT_BODY,
                legend_font_size,
            )
            required_width = label_width + 20
            if legend_x + required_width > drawing_width - 18:
                legend_x = 42
                legend_y -= 12

            drawing.add(Rect(
                legend_x,
                legend_y,
                7,
                7,
                fillColor=item.color,
                strokeColor=item.color,
            ))
            drawing.add(String(
                legend_x + 11,
                legend_y,
                item.name,
                fontName=Theme.FONT_BODY,
                fontSize=legend_font_size,
                fillColor=MUTED_COLOR,
            ))
            legend_x += required_width
            
        if note:
            drawing.add(String(
                18,
                7,
                note,
                fontName=Theme.FONT_BODY,
                fontSize=6.5,
                fillColor=MUTED_COLOR,
            ))
        return drawing

    @staticmethod
    def _price_chart(
        report: Report,
        period: str,
        width: float,
    ) -> Drawing | None:
        points: list[YFinanceHistoryPoint] = PDFRenderer._history_points(report, period)
        if len(points) < 2:
            return None
        dates: list[date] = [point.date for point in points]
        closes: list[float] = [float(point.close) for point in points]
        windows: dict[str, tuple[int, int]] = {
            '5y': (50, 200),
            '1y': (20, 50),
            '3mo': (5, 20),
            '1w': (0, 0),
        }
        short_window, long_window = windows[period]
        series: list[ChartSeries] = [
            ChartSeries(
                _ui(report, 'chart.series.price', 'Price'),
                list(enumerate(closes)),
                CHART_PRIMARY_COLOR,
            ),
        ]

        if short_window and (avg := PDFRenderer._moving_average(closes, short_window)):
            series.append(ChartSeries(
                _ui(report, 'chart.series.moving_average_short', 'Short moving average'),
                avg,
                CHART_SECONDARY_COLOR,
            ))
        
        if long_window and (avg := PDFRenderer._moving_average(closes, long_window)):
            series.append(ChartSeries(
                _ui(report, 'chart.series.moving_average_long', 'Long moving average'),
                avg,
                CHART_TERTIARY_COLOR,
            ))
        
        return PDFRenderer._chart_drawing(
            report,
            f'price_history_{period}',
            series,
            dates,
            width,
        )

    @staticmethod
    def _aligned_normalized_series(
        primary: list[YFinanceHistoryPoint],
        comparison: list[YFinanceHistoryPoint],
    ) -> tuple[list[date], list[float], list[float]]:
        comparison_by_date: dict[date, float] = {
            point.date: float(point.close)
            for point in comparison
            if point.close is not None
        }
        pairs: list[tuple[date, float, float]] = [
            (point.date, float(point.close), comparison_by_date[point.date])
            for point in primary
            if point.close is not None and point.date in comparison_by_date
        ]

        if len(pairs) < 2:
            return [], [], []

        dates, primary_values, comparison_values = zip(*pairs)
        return (
            list(dates),
            list(PDFRenderer._indexed(list(primary_values))),
            list(PDFRenderer._indexed(list(comparison_values))),
        )

    @staticmethod
    def _charts(
        report: Report,
        styles: dict[str, ParagraphStyle],
        width: float,
    ) -> list[Flowable]:
        points: list[YFinanceHistoryPoint] = PDFRenderer._history_points(report, '10y')
        short_points: list[YFinanceHistoryPoint] = PDFRenderer._history_points(report, '5y')
        if len(points) < 2 and len(short_points) < 2:
            return []
        
        if len(points) < 2:
            points = short_points

        dates: list[date] = [point.date for point in points]
        closes: list[float] = [float(point.close) for point in points]
        history: list[YFinanceHistoryPoint] = report.analysis.history_10y_1mo
        charts: list[tuple[str, Drawing | None]] = []

        for period in ('5y', '1y', '3mo', '1w'):
            charts.append((
                f'price_history_{period}',
                PDFRenderer._price_chart(report, period, width),
            ))

        sp500_points: list[YFinanceHistoryPoint] = PDFRenderer._sp500_points(report)
        relative_dates, relative_price, relative_sp500 = (
            PDFRenderer._aligned_normalized_series(points, sp500_points)
            if sp500_points
            else ([], [], [])
        )
        charts.append((
            'relative_performance',
            PDFRenderer._chart_drawing(
                report,
                'relative_performance',
                [
                    ChartSeries(
                        _ui(report, 'chart.series.price', 'Price'),
                        relative_price,
                        CHART_PRIMARY_COLOR,
                    ),
                    ChartSeries(
                        _ui(report, 'chart.series.sp500', 'S&P 500'),
                        relative_sp500,
                        CHART_SECONDARY_COLOR,
                    ),
                ],
                relative_dates,
                width,
                note=(
                    None
                    if relative_dates
                    else _ui(report, 'chart.benchmark_unavailable', '')
                ),
            ),
        ))

        running_max: float = closes[0]
        drawdown_values: list[float] = []
        for value in closes:
            running_max = max(running_max, value)
            drawdown_values.append((value / running_max - 1) * 100)
        
        charts.append((
            'drawdown',
            PDFRenderer._chart_drawing(
                report,
                'drawdown',
                [ChartSeries(
                    _ui(report, 'chart.series.drawdown', 'Drawdown'),
                    list(enumerate(drawdown_values)),
                    CHART_QUATERNARY_COLOR,
                )],
                dates,
                width,
            ),
        ))

        revenue: list[YFinanceHistoryPoint] = PDFRenderer._metric_points(history.revenue)
        earnings: list[YFinanceHistoryPoint] = PDFRenderer._metric_points(history.earnings)
        free_cash_flow: list[YFinanceHistoryPoint] = PDFRenderer._metric_points(history.free_cash_flow)
        growth_series: list[ChartSeries] = []
        growth_dates: list[str] = dates
        for name, points_for_metric, color in (
            ('revenue', revenue, CHART_PRIMARY_COLOR),
            ('earnings', earnings, CHART_SECONDARY_COLOR),
            ('free_cash_flow', free_cash_flow, CHART_TERTIARY_COLOR),
        ):
            if len(points_for_metric) >= 2:
                growth_series.append(ChartSeries(
                    _ui(report, f'chart.series.{name}', name.title()),
                    PDFRenderer._indexed([point.value for point in points_for_metric]),
                    color,
                ))
                growth_dates = [point.date for point in points_for_metric]
        charts.append((
            'fundamental_growth',
            PDFRenderer._chart_drawing(
                report,
                'fundamental_growth',
                growth_series,
                growth_dates,
                width,
            ),
        ))

        dividend_points = PDFRenderer._metric_points(history.dividends)
        charts.append((
            'dividends_history',
            PDFRenderer._chart_drawing(
                report,
                'dividends_history',
                [ChartSeries(
                    _ui(report, 'chart.series.dividends', 'Dividends'),
                    list(enumerate(point.value for point in dividend_points)),
                    CHART_SECONDARY_COLOR,
                )] if len(dividend_points) >= 2 else [],
                [point.date for point in dividend_points],
                width,
            ),
        ))

        fundamental_inputs: list[list[float]] = []
        for points_for_metric in (revenue, free_cash_flow):
            if len(points_for_metric) >= 2:
                fundamental_inputs.append([
                    value
                    for _, value in PDFRenderer._indexed(
                        [point.value for point in points_for_metric],
                    )
                ])
        if fundamental_inputs:
            proxy = [
                sum(values[index] for values in fundamental_inputs) / len(fundamental_inputs)
                for index in range(min(map(len, fundamental_inputs)))
            ]
            market_index = PDFRenderer._indexed(closes)
            proxy_dates = dates[:len(proxy)]
            proxy_series = [
                ChartSeries(
                    _ui(report, 'chart.series.price', 'Price'),
                    market_index[:len(proxy)],
                    CHART_PRIMARY_COLOR,
                ),
                ChartSeries(
                    _ui(report, 'chart.series.fundamental_proxy', 'Fundamental proxy'),
                    list(enumerate(proxy)),
                    CHART_TERTIARY_COLOR,
                ),
            ]
            charts.append((
                'fundamental_value',
                PDFRenderer._chart_drawing(
                    report,
                    'fundamental_value',
                    proxy_series,
                    proxy_dates,
                    width,
                    note=_ui(report, 'chart.proxy_note', ''),
                ),
            ))
            charts.append((
                'fair_value',
                PDFRenderer._chart_drawing(
                    report,
                    'fair_value',
                    proxy_series,
                    proxy_dates,
                    width,
                    note=_ui(report, 'chart.proxy_note', ''),
                ),
            ))

        valuation_series: list[ChartSeries] = []
        valuation_dates: list[datetime.date] = dates
        for name, fact, color in (
            ('pe_ratio', history.pe_ratio, CHART_PRIMARY_COLOR),
            ('price_to_fcf', history.price_to_fcf, CHART_SECONDARY_COLOR),
            ('ev_to_ebitda', history.ev_to_ebitda, CHART_TERTIARY_COLOR),
            ('price_to_sales', history.price_to_sales, CHART_QUATERNARY_COLOR),
            ('peg_ratio', history.peg_ratio, CHART_PRIMARY_COLOR),
        ):
            metric_points = PDFRenderer._metric_points(fact)
            if len(metric_points) >= 2:
                valuation_series.append(ChartSeries(
                    _translation(report, f'valuation.{name}', name.replace('_', ' ').title()),
                    list(enumerate(point.value for point in metric_points)),
                    color,
                ))
                valuation_dates = [point.date for point in metric_points]
        charts.append((
            'valuation_history',
            PDFRenderer._chart_drawing(
                report,
                'valuation_history',
                valuation_series,
                valuation_dates,
                width,
            ),
        ))

        if not any(drawing is not None for _, drawing in charts):
            return []
        story: list[Flowable] = [
            _paragraph(
                escape(_ui(report, 'section.charts', 'Market charts')),
                styles['eyebrow'],
            ),
            Spacer(1, 10),
        ]
        for chart_name, drawing in charts:
            if drawing is None or not PDFRenderer._chart_requested(report, chart_name):
                continue
            story.extend([drawing, Spacer(1, 12)])
        return story
