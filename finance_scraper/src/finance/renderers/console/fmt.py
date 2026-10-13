
from datetime import datetime
from designkit.structural import decorador as deco
from designkit.behavioral.typing import Assertion, classname
from typing import Literal, Callable, Iterable


from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.console import Group, RenderableType
from rich.padding import Padding

from finance.services.llm.models import Reasoning
from datatypes import Money, Percentage
from finance.services.stock_analyzer.models import Fact, Metric, MetricGrade, MetricValue



# ================================================== #
# TYPE ALIASES                                       #
# ================================================== #

type MetricEvalType = Literal['rating', 'comparison']



# ================================================== #
# HELPER FEATURES                                    #
# ================================================== #

def style(content: str, grade: MetricGrade) -> str:
    match grade:
        case MetricGrade.EXCELLENT:
            return f'[excellent]{content}[/excellent]'
        case MetricGrade.VERY_GOOD:
            return f'[very_good]{content}[/very_good]'
        case MetricGrade.GOOD:
            return f'[good]{content}[/good]'
        case MetricGrade.MEH:
            return f'[meh]{content}[/meh]'
        case MetricGrade.BAD:
            return f'[bad]{content}[/bad]'
        case MetricGrade.VERY_BAD:
            return f'[very_bad]{content}[/very_bad]'
        case MetricGrade.AWFUL:
            return f'[awful]{content}[/awful]'
        case MetricGrade.NA:
            return f'[dim]{content}[/dim]'
        case MetricGrade.NaN:
            return f'[purple]{content}[/purple]'
        case _ as grade:
            raise ValueError(f'Unknown metric grade: {grade}')


def _display_value(metric: Metric) -> float | int | None:
    if Assertion(metric).should_be(Metric):
        return float(metric.metric)
    return metric.metric


def _default_value_grade(value: float | int | None) -> MetricGrade:
    if isinstance(value, (int, float)) and value < 0:
        return MetricGrade.BAD
    return MetricGrade.GOOD


def _styled_metric_text(
    metric: Metric,
    *,
    want_text: bool,
    grade: MetricGrade,
    pre: str,
    post: str,
    ndigits: int,
) -> str:
    label = metric.label or 'N/A'
    if want_text:
        return f'[{grade}]{label}[/{grade}]'

    value = _display_value(metric)
    if grade == MetricGrade.NA:
        grade = _default_value_grade(value)
    return style(f'{pre}{value:.{ndigits}f}{post}', grade)


def _metric_grade(metric: Metric, metric_eval: MetricEvalType) -> MetricGrade:
    if metric_eval == 'comparison':
        return (metric.comparison or (MetricGrade.NA, None, None))[0]
    if metric_eval == 'rating':
        return (metric.rating or (MetricGrade.NA, None))[0]
    raise ValueError(f'Unknown metric evaluation type: {metric_eval}')


def _fmt(metric: Metric, format: Literal['label', 'value'] = 'label', metric_eval: MetricEvalType = 'rating', *, pre: str = '', post: str = '', ndigits: int = 2, dtype: type = float) -> str:
    want_text: bool = format == 'label'

    if metric.unavailable:
        return '[dim]Unavailable[/dim]'
    if metric.is_miss or metric.is_nan:
        return '[dim]N/A[/dim]'
    return _styled_metric_text(
        metric,
        want_text=want_text,
        grade=_metric_grade(metric, metric_eval),
        pre=pre,
        post=post,
        ndigits=ndigits,
    )

def _get_str(text: str | Fact) -> str:
    return str(text.value) if isinstance(text, Fact) else text


def _grade(metric: Metric, metric_eval: MetricEvalType) -> MetricGrade:
    if metric_eval == 'comparison':
        return (
            metric.comparison[0]
            if metric.comparison
            else MetricGrade.NA
        )
    return metric.rating[0] if metric.rating else MetricGrade.NA


def _money_text(metric: Metric, *, metric_eval: MetricEvalType, ndigits: int = 2) -> str:
    if metric.unavailable:
        return '[dim]Unavailable[/dim]'
    
    if metric.is_miss:
        return '[dim]N/A[/dim]'

    money: MetricValue = metric.value
    Assertion(money).must_be(Money)

    formatted: str = money.currency.format_amount(money.value, 'formal', ndigits)
    grade: MetricGrade = _grade(metric, metric_eval)
    if grade == MetricGrade.NA:
        grade = (
            MetricGrade.BAD
            if money.is_negative()
            else MetricGrade.GOOD
        )
    return style(formatted, grade)


def _has_positive_change(delta: float | None, delta_pct: float | None) -> bool:
    return (
        (delta_pct is not None and delta_pct >= 0)
        or (delta is not None and delta >= 0)
    )

def justify(text: str) -> Text:
    return Text.from_markup(text, justify='full')



# ================================================== #
# FORMATTERS                                         #
# ================================================== #

def as_text(text: str | Fact, *, metric_eval: MetricEvalType = 'rating') -> str:
    return f'[dim]{_get_str(text)}[/dim]'

def as_link(text: Fact, url: str, style: str = 'link', *, metric_eval: MetricEvalType = 'rating') -> str:
    return f'[link={url}][{style}]{_get_str(text)}[/{style}][/link]'

def as_lowkey_link(text: Fact, url: str, *, metric_eval: MetricEvalType = 'rating') -> str:
    return f'[link={url}]{_get_str(text)}[/link]'

def as_date(date: datetime, style: str = 'date', *, metric_eval: MetricEvalType = 'rating') -> str:
    formatted_date: str = date.strftime('%Y-%m-%d')
    return f'[{style}]{formatted_date}[/{style}]'

def as_timestamp(timestamp: datetime, style: str = 'date', *, metric_eval: MetricEvalType = 'rating') -> str:
    formatted_timestamp: str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
    return f'[{style}]{formatted_timestamp}[/{style}]'

def as_point(reasoning: Reasoning, content: str, *, metric_eval: MetricEvalType = 'rating') -> str:
    Assertion(reasoning).must_be(Reasoning)
    Assertion(content).must_be(str)

    match reasoning:
        case Reasoning.POSITIVE:
            return f'[positive]\\[{reasoning.value}] {content}[/positive]'
        case Reasoning.NEUTRAL:
            return f'[neutral]\\[{reasoning.value}] {content}[/neutral]'
        case Reasoning.NEGATIVE:
            return f'[negative]\\[{reasoning.value}] {content}[/negative]'
        case _ as reasoning:
            raise ValueError(f'Unknown reasoning type: {reasoning}')

def as_percent(metric: Metric, *, metric_eval: MetricEvalType = 'rating') -> str:
    display_metric = metric.model_copy(
        update={
            'metric': (
                float(Percentage.from_fraction(metric.metric))
                if metric.metric is not None
                else None
            )
        }
    )
    return _fmt(display_metric, 'value', pre='', post='%', ndigits=3, dtype=float, metric_eval=metric_eval)

def as_currency(metric: Metric, *, metric_eval: MetricEvalType = 'rating') -> str:
    if Assertion(metric).should_be(Metric):
        return _money_text(metric, metric_eval=metric_eval)

def as_price(metric: Metric, *, metric_eval: MetricEvalType = 'comparison') -> str:
    Assertion(metric).must_be(Metric, None)

    if metric.value is None:
        return _fmt(metric, format='label')

    if metric.comparison is None:
        return as_currency(metric, metric_eval='rating')

    rating, delta, delta_pct = metric.comparison
    formatted: str = metric.value.currency.format_amount(metric.value.value, 'formal')

    if _has_positive_change(delta, delta_pct):
        return f'[gain]{formatted}[/gain]'
    return f'[loss]{formatted}[/loss]'

def as_integer(metric: Metric, *, metric_eval: MetricEvalType = 'rating') -> str:
    return _fmt(metric, 'value', pre='', post='', ndigits=0, dtype=int, metric_eval=metric_eval)

def as_number(metric: Metric, ndigits: int = 2, *, metric_eval: MetricEvalType = 'rating') -> str:
    return _fmt(metric, 'value', pre='', post='', ndigits=ndigits, dtype=float, metric_eval=metric_eval)

def as_multiple(metric: Metric, *, metric_eval: MetricEvalType = 'rating') -> str:
    return _fmt(metric, 'value', pre='x', ndigits=2, dtype=float, metric_eval=metric_eval)

def as_table(
    metric: Metric,
    label: str,
    fmt_func: Callable[[Metric], str],
    *,
    metric_eval: MetricEvalType = 'rating',
    show_rating: bool = True,
) -> Table:
    grid: Table = Table.grid()
    desc: str = (
        '...'
        if metric.unavailable
        else _fmt(metric, 'label', metric_eval=metric_eval)
        if show_rating or metric.is_miss
        else ''
    )
    label: str = label
    value: str = fmt_func(metric)

    if desc:
        grid.add_row(
            Align.center(
                Text.from_markup(
                    desc,
                    justify='full'
                ),
            ),
        )
    grid.add_row(
        f'{label}: {value}'
    )

    return grid

def as_metric_section(renderable_metrics: Iterable[RenderableType], grid: tuple[int, int]) -> Table:
    section: Table = Table.grid(expand=True)
    
    expected_metrics: int = grid[0] * grid[1]
    total_metrics: int = len(renderable_metrics)

    if expected_metrics != total_metrics:
        raise ValueError(f'Expected {expected_metrics} metrics for this section, but got {total_metrics}.')
    
    for i in range(0, total_metrics, grid[1]):
        section.add_row(*renderable_metrics[i:i+grid[1]])
    return section


# ================================================== #
# HELPERS FORMATTED                               #
# ================================================== #

def with_percentage(formatted: str, metric: Metric, *, metric_eval: MetricEvalType = 'comparison') -> str:
    if metric.comparison is None:
        return formatted

    rating, _, delta_pct = metric.comparison
    if delta_pct is None:
        return formatted

    status: str = 'gain' if _has_positive_change(None, delta_pct) else 'loss'
    return f'{formatted} ([{status}]{delta_pct:.3f}[/{status}])'
