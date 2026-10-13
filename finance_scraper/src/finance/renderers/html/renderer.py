# ================================================== #
# MODULE: renderer
# ================================================== #


import json
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Final as Const

from finance.config import APP_AUTHOR, APP_NAME, APP_NAME_CODING, Theme
from finance.services.i18n import i18n, translate as ui_translate
from finance.renderers.pdf.renderer import METRIC_SPECS
from finance.renderers.utils import normalize_output
from finance.services.reporter import Report
from finance.services.stock_analyzer.models import Fact, Metric, MetricStatus
from datatypes import Money, Percentage
from finance.types.report_presets import ReportPreset, get_preset


CSS: Const[str] = '''
:root {
  --bg: THEME_SURFACE;
  --card: THEME_CARD;
  --ink: THEME_INK;
  --muted: THEME_MUTED;
  --rule: THEME_RULE;
  --accent: THEME_ACCENT;
  --link: THEME_LINK;
  --positive: THEME_GAIN;
  --negative: THEME_LOSS;
  --header: THEME_PAGE;
  --font-body: THEME_FONT_BODY;
  --font-display: THEME_FONT_DISPLAY;
  --shadow: 0 16px 42px rgba(20, 32, 48, .08);
  --shadow-hover: 0 20px 48px rgba(20, 32, 48, .14);
}
* { box-sizing: border-box; }
html { background: var(--bg); scroll-behavior: smooth; }
body {
  background:
    radial-gradient(circle at 88% -12%, rgba(41, 148, 255, .14), transparent 30rem),
    radial-gradient(circle at 2% 22%, rgba(0, 212, 187, .08), transparent 25rem),
    var(--bg);
  color: var(--ink);
  font-family: var(--font-body);
  margin: 0;
  min-width: 320px;
}
a { color: var(--link); text-underline-offset: .18em; }
a:focus-visible, button:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--link) 45%, transparent);
  outline-offset: 3px;
}
.app-header {
  align-items: center;
  background: rgba(255, 255, 255, .88);
  backdrop-filter: blur(18px);
  border-bottom: 1px solid color-mix(in srgb, var(--rule) 78%, transparent);
  display: flex;
  gap: 1rem;
  min-height: 70px;
  padding: 0 4vw;
}
.menu-icon {
  align-items: center;
  background: var(--header);
  border-radius: .7rem;
  color: var(--card);
  display: inline-flex;
  font-size: .9rem;
  height: 2rem;
  justify-content: center;
  width: 2rem;
}
.brand {
  color: var(--ink);
  font-family: var(--font-display);
  font-size: 1.05rem;
  font-weight: 800;
  letter-spacing: -.02em;
  text-decoration: none;
}
.brand-badge {
  background: color-mix(in srgb, var(--accent) 12%, var(--card));
  border-radius: 999px;
  color: var(--accent);
  font-size: .63rem;
  font-weight: 800;
  letter-spacing: .08em;
  padding: .3rem .55rem;
  text-transform: uppercase;
}
.global-nav { display: flex; gap: .15rem; margin-left: auto; }
.global-nav a {
  border-radius: .55rem;
  color: var(--muted);
  font-size: .78rem;
  font-weight: 700;
  padding: .6rem .75rem;
  text-decoration: none;
}
.global-nav a:hover, .global-nav a.active {
  background: color-mix(in srgb, var(--link) 9%, var(--card));
  color: var(--ink);
}
.header-meta { color: var(--muted); font-size: .73rem; font-weight: 600; }
.shell { margin: 0 auto; max-width: 1240px; padding: 2.8rem 4vw 4.5rem; }
.instrument-bar {
  align-items: center;
  display: flex;
  gap: 1rem;
  margin-bottom: 1.35rem;
}
.instrument-mark {
  align-items: center;
  background: var(--card);
  border: 1px solid var(--rule);
  border-radius: 50%;
  box-shadow: 0 9px 22px rgba(20, 32, 48, .12);
  display: flex;
  height: 2.8rem;
  justify-content: center;
  overflow: hidden;
  padding: .24rem;
  width: 2.8rem;
}
.instrument-mark img { border-radius: 50%; height: 100%; object-fit: contain; width: 100%; }
.instrument-mark-missing::after {
  color: var(--ink);
  content: attr(data-fallback);
  font-family: var(--font-display);
  font-size: .78rem;
  font-weight: 800;
}
.instrument-name { font-family: var(--font-display); font-size: 1.05rem; font-weight: 800; }
.instrument-subtitle { color: var(--muted); font-size: .8rem; font-weight: 500; }
.layout { display: grid; gap: 1.1rem; grid-template-columns: minmax(0, 1fr) 280px; }
.main-column, .side-column { min-width: 0; }
.side-column { align-content: start; display: grid; gap: 1rem; }
.side-column .panel { padding: 1.4rem; }
.panel, .metric-card, .chart-card, .news-card {
  background: var(--card);
  border: 1px solid color-mix(in srgb, var(--rule) 82%, transparent);
  border-radius: 1.15rem;
  box-shadow: var(--shadow);
}
.panel { padding: 1.35rem; }
.price-panel {
  background:
    linear-gradient(120deg, color-mix(in srgb, var(--link) 9%, var(--card)), transparent 55%),
    var(--card);
}
.price-panel h1 {
  font-family: var(--font-display);
  font-size: 1.62rem;
  font-weight: 800;
  letter-spacing: -.04em;
  margin: 0 0 .4rem;
}
.price {
  color: var(--ink);
  font-family: var(--font-display);
  font-size: clamp(2.25rem, 5vw, 3.05rem);
  font-weight: 800;
  letter-spacing: -.065em;
}
.price-unit { color: var(--muted); font-size: .82rem; font-weight: 700; margin-left: .25rem; }
.change { color: var(--muted); font-size: .84rem; font-weight: 700; margin-top: .85rem; }
.positive { color: var(--positive) !important; }
.negative { color: var(--negative) !important; }
.eyebrow {
  color: var(--accent);
  font-size: .65rem;
  font-weight: 800;
  letter-spacing: .13em;
  text-transform: uppercase;
}
.section { margin-top: 2.2rem; scroll-margin-top: 6rem; }
.section-heading {
  align-items: baseline;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
  margin-bottom: .85rem;
}
.section-heading h2 {
  font-family: var(--font-display);
  font-size: 1.32rem;
  font-weight: 800;
  letter-spacing: -.035em;
  margin: 0;
}
.section-heading p { color: var(--muted); font-size: .78rem; line-height: 1.5; margin: .15rem 0 0; }
.cards { display: grid; gap: .75rem; grid-template-columns: repeat(4, minmax(0, 1fr)); }
.stat-card { box-shadow: none; padding: 1rem; }
.stat-label, .metric-label {
  color: var(--muted);
  font-size: .64rem;
  font-weight: 800;
  letter-spacing: .07em;
  text-transform: uppercase;
}
.stat-value { font-family: var(--font-display); font-size: 1.12rem; font-weight: 800; margin: .35rem 0; }
.stat-note, .muted { color: var(--muted); font-size: .77rem; line-height: 1.55; }
.market-links { display: grid; gap: .65rem; margin-top: 1.15rem; }
.market-link {
  align-items: center;
  background: color-mix(in srgb, var(--link) 5%, var(--card));
  border: 1px solid var(--rule);
  border-radius: .8rem;
  color: var(--ink);
  display: flex;
  gap: .75rem;
  justify-content: space-between;
  padding: .78rem .82rem;
  text-decoration: none;
  transition: background .18s ease, border-color .18s ease, transform .18s ease;
}
.market-link:hover { background: color-mix(in srgb, var(--link) 10%, var(--card)); border-color: var(--link); transform: translateY(-1px); }
.market-link strong { display: block; font-size: .8rem; }
.market-link small { color: var(--muted); display: block; font-size: .67rem; margin-top: .16rem; }
.market-link-arrow { color: var(--link); font-size: 1rem; }
.aside-facts { display: grid; gap: .75rem; margin-top: 1.1rem; }
.aside-fact { border-bottom: 1px solid color-mix(in srgb, var(--rule) 76%, transparent); display: grid; gap: .2rem; padding-bottom: .7rem; }
.aside-fact:last-child { border-bottom: 0; padding-bottom: 0; }
.aside-fact span { color: var(--muted); font-size: .65rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.aside-fact strong { font-size: .82rem; overflow-wrap: anywhere; }
.profile { display: grid; grid-template-columns: 1fr 1fr; padding: 0; }
.profile-row {
  border-bottom: 1px solid color-mix(in srgb, var(--rule) 76%, transparent);
  display: grid;
  gap: 1rem;
  grid-template-columns: 8rem minmax(0, 1fr);
  padding: .78rem 1rem;
}
.profile-row strong { font-size: .75rem; font-weight: 800; }
.profile-row span { font-size: .8rem; font-weight: 500; overflow-wrap: anywhere; }
.metric-toolbar {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: .45rem;
  justify-content: flex-end;
}
.metric-toolbar-label {
  color: var(--muted);
  font-size: .68rem;
  font-weight: 800;
  letter-spacing: .06em;
  text-transform: uppercase;
}
.metric-filter {
  background: transparent;
  border: 1px solid var(--rule);
  border-radius: 999px;
  color: var(--muted);
  cursor: pointer;
  font: inherit;
  font-size: .7rem;
  font-weight: 700;
  padding: .34rem .58rem;
  transition: background .18s ease, border-color .18s ease, color .18s ease;
}
.metric-filter:hover, .metric-filter[aria-pressed="true"] {
  background: var(--ink);
  border-color: var(--ink);
  color: var(--card);
}
.metric-grid { display: grid; gap: .75rem; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.metric-card {
  min-height: 9.1rem;
  padding: 1rem;
  transition: box-shadow .18s ease, transform .18s ease;
}
.metric-card:hover { box-shadow: var(--shadow-hover); transform: translateY(-2px); }
.metric-card-top { align-items: flex-start; display: flex; gap: .65rem; justify-content: space-between; }
.metric-card .metric-label { line-height: 1.35; max-width: 13rem; }
.metric-value {
  color: var(--ink);
  font-family: var(--font-display);
  font-size: 1.28rem;
  font-weight: 800;
  letter-spacing: -.035em;
  margin: 1.3rem 0 .45rem;
}
.metric-status {
  align-items: center;
  background: color-mix(in srgb, var(--status) 12%, var(--card));
  border-radius: 999px;
  color: color-mix(in srgb, var(--status) 82%, var(--ink));
  display: inline-flex;
  flex: 0 0 auto;
  font-size: .64rem;
  font-weight: 800;
  gap: .32rem;
  line-height: 1;
  max-width: 65%;
  overflow: hidden;
  padding: .34rem .45rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.metric-status::before {
  background: var(--status);
  border-radius: 50%;
  content: "";
  height: .42rem;
  width: .42rem;
}
.metric-empty {
  background: color-mix(in srgb, var(--muted) 6%, var(--card));
  border: 1px dashed var(--rule);
  border-radius: 1rem;
  color: var(--muted);
  font-size: .82rem;
  margin: .75rem 0 0;
  padding: 1rem;
  text-align: center;
}
.prediction { display: grid; gap: 1.35rem; grid-template-columns: 1fr 1fr; }
.signal { color: var(--positive); font-family: var(--font-display); font-size: 1.9rem; font-weight: 800; margin: .35rem 0; }
.probabilities { display: grid; gap: .6rem; }
.probability { align-items: center; display: grid; gap: .6rem; grid-template-columns: 5rem minmax(0, 1fr) 4rem; }
.bar { background: #edf0f4; border-radius: 99px; height: .48rem; overflow: hidden; }
.bar i { background: linear-gradient(90deg, var(--link), #7c3aed); display: block; height: 100%; }
.chart-tabs { display: flex; flex-wrap: wrap; gap: .45rem; margin-bottom: .75rem; }
.chart-tab {
  background: var(--card);
  border: 1px solid var(--rule);
  border-radius: .65rem;
  color: var(--muted);
  cursor: pointer;
  font: inherit;
  font-size: .72rem;
  font-weight: 800;
  padding: .43rem .66rem;
}
.chart-tab:hover, .chart-tab[aria-selected="true"] {
  background: var(--header);
  border-color: var(--header);
  color: var(--card);
}
.chart-grid { display: grid; gap: .85rem; grid-template-columns: minmax(0, 1fr); }
.chart-card { min-height: 440px; overflow: hidden; padding: 1rem; }
.chart-card h3 { font-family: var(--font-display); font-size: 1rem; font-weight: 800; margin: .15rem 0 .25rem; }
.chart-card > p { margin: 0 0 .7rem; }
.tv-container { height: 350px; }
.news-list { display: grid; gap: .7rem; }
.news-card { padding: 1rem 1.1rem; }
.news-card h3 { font-family: var(--font-display); font-size: .98rem; font-weight: 800; margin: 0 0 .35rem; }
.footer {
  border-top: 1px solid color-mix(in srgb, var(--rule) 80%, transparent);
  color: var(--muted);
  display: flex;
  font-size: .71rem;
  font-weight: 600;
  justify-content: space-between;
  padding: 1rem 4vw 1.5rem;
}
.empty { color: var(--muted); padding: 1.5rem; text-align: center; }
@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; }
  .side-column { order: -1; }
  .global-nav { margin-left: 0; }
  .header-meta { display: none; }
  .section-heading { align-items: flex-start; flex-direction: column; }
  .metric-toolbar { justify-content: flex-start; }
}
@media (max-width: 680px) {
  .app-header { flex-wrap: wrap; padding: .8rem 1rem; }
  .global-nav { order: 3; overflow-x: auto; width: 100%; }
  .global-nav a { padding: .65rem .55rem .55rem; }
  .shell { padding: 1.2rem 1rem 2.5rem; }
  .instrument-bar { margin-top: .3rem; }
  .cards, .metric-grid, .chart-grid, .profile, .prediction { grid-template-columns: 1fr; }
  .metric-card { min-height: auto; }
  .metric-status { max-width: 57%; }
  .profile-row { grid-template-columns: minmax(6.2rem, .7fr) minmax(0, 1fr); }
  .footer { align-items: flex-start; flex-direction: column; gap: .35rem; padding-inline: 1rem; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; transition-duration: .01ms !important; }
}
'''


_JAVASCRIPT: Const[str] = f'''
(function () {{
  const scriptUrl = {json.dumps(Theme.TRADINGVIEW_WIDGET_URL)};

  function mountWidget(container) {{
    if (!container || container.dataset.widgetLoaded === 'true') {{
      return;
    }}
    const widget = document.createElement('script');
    widget.type = 'text/javascript';
    widget.src = scriptUrl;
    widget.async = true;
    widget.text = container.dataset.tvConfig;
    const mount = container.querySelector('.tradingview-widget-container__widget');
    if (!mount) {{
      return;
    }}
    mount.appendChild(widget);
    container.dataset.widgetLoaded = 'true';
  }}

  function initializeMetricFilters() {{
    document.querySelectorAll('[data-metric-controls]').forEach(function (controls) {{
      controls.addEventListener('click', function (event) {{
        const button = event.target.closest('[data-metric-filter]');
        if (!button) {{
          return;
        }}
        const section = controls.closest('[data-metric-section]');
        if (!section) {{
          return;
        }}
        const selected = button.dataset.metricFilter;
        const cards = section.querySelectorAll('[data-metric-card]');
        let visibleCards = 0;
        cards.forEach(function (card) {{
          const visible = selected === 'all' || card.dataset.metricStatus === selected;
          card.hidden = !visible;
          if (visible) {{
            visibleCards += 1;
          }}
        }});
        controls.querySelectorAll('[data-metric-filter]').forEach(function (filter) {{
          filter.setAttribute('aria-pressed', String(filter === button));
        }});
        const empty = section.querySelector('[data-metric-empty]');
        if (empty) {{
          empty.hidden = visibleCards !== 0;
        }}
      }});
    }});
  }}

  function initializeCharts() {{
    document.querySelectorAll('[data-chart-tabs]').forEach(function (tabs) {{
      const section = tabs.closest('[data-chart-section]');
      if (!section) {{
        return;
      }}
      const activate = function (button) {{
        const target = button.dataset.chartTarget;
        section.querySelectorAll('[data-chart-panel]').forEach(function (panel) {{
          const isSelected = panel.dataset.chartPanel === target;
          panel.hidden = !isSelected;
          if (isSelected) {{
            mountWidget(panel.querySelector('[data-tv-config]'));
          }}
        }});
        tabs.querySelectorAll('[data-chart-target]').forEach(function (tab) {{
          const isSelected = tab === button;
          tab.setAttribute('aria-selected', String(isSelected));
          tab.tabIndex = isSelected ? 0 : -1;
        }});
      }};
      tabs.addEventListener('click', function (event) {{
        const button = event.target.closest('[data-chart-target]');
        if (button) {{
          activate(button);
        }}
      }});
      const initial = tabs.querySelector('[data-chart-target][aria-selected="true"]');
      if (initial) {{
        activate(initial);
      }}
    }});
  }}

  function initialize() {{
    initializeMetricFilters();
    initializeCharts();
  }}

  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', initialize, {{ once: true }});
  }} else {{
    initialize();
  }}
}})();
'''


_TAILWIND_CONFIG: Const[str] = (
    'tailwind.config = ' + json.dumps({
        'theme': {
            'extend': {
                'fontFamily': {
                    'sans': list(Theme.FONT_BODY_STACK),
                    'display': list(Theme.FONT_DISPLAY_STACK),
                },
            },
        },
    }) + ';'
)


def _css() -> str:
    replacements = {
        'THEME_SURFACE': Theme.COLOR_SURFACE,
        'THEME_CARD': Theme.COLOR_CARD,
        'THEME_INK': Theme.COLOR_INK,
        'THEME_MUTED': Theme.COLOR_MUTED,
        'THEME_RULE': Theme.COLOR_RULE,
        'THEME_ACCENT': Theme.COLOR_ACCENT,
        'THEME_LINK': Theme.COLOR_LINK,
        'THEME_GAIN': Theme.COLOR_GAIN,
        'THEME_LOSS': Theme.COLOR_LOSS,
        'THEME_PAGE': Theme.COLOR_PAGE_BACKGROUND,
        'THEME_FONT_BODY': Theme.FONT_BODY_CSS,
        'THEME_FONT_DISPLAY': Theme.FONT_DISPLAY_CSS,
    }
    css = CSS
    for key, value in replacements.items():
        css = css.replace(key, value)
    return css


def _ui(report: Report, key: str, fallback: str) -> str:
    return ui_translate(
        report.account.language,
        key,
        fallback,
        throw_error=False,
    )


def _analyzer_translation(
    report: Report,
    mnemonic: str,
    fallback: str,
    field: str = 'title',
) -> str:
    language = report.account.language
    snapshot = i18n(
        f'analyzer.{mnemonic}',
        language,
        throw_error=False,
    )('.', throw_error=False)
    return getattr(snapshot, field, None) or fallback


def _safe(value: object) -> str:
    if isinstance(value, Fact):
        value = value.value
    if value is None:
        return 'N/A'
    return str(value)


def _first_text(*values: object) -> str:
    for value in values:
        text = _safe(value)
        if text != 'N/A':
            return text
    return 'N/A'


def _quote_type(report: Report) -> str:
    raw = _safe(report.analysis.descriptive_facts.quote_type)
    normalized = ''.join(character for character in raw.lower() if character.isalnum())
    aliases = {
        'equity': 'equity',
        'stock': 'stock',
        'etf': 'etf',
        'mutualfund': 'mutualfund',
        'fund': 'mutualfund',
        'reit': 'realestate',
        'realestate': 'realestate',
    }
    return _ui(report, f'quote_type.{aliases.get(normalized, normalized)}', raw)


def _status_color(metric: Metric) -> str:
    return {
        MetricStatus.OK: Theme.COLOR_GAIN,
        MetricStatus.NA: Theme.COLOR_NEUTRAL,
        MetricStatus.NaN: Theme.COLOR_AWFUL,
        MetricStatus.NOT_AVAILABLE: Theme.COLOR_NEUTRAL,
        MetricStatus.NOT_RATED: Theme.COLOR_NUMBER,
    }[metric.status]


def _status_text(report: Report, metric: Metric) -> str:
    if metric.status == MetricStatus.OK and metric.label:
        return metric.label
    return _ui(
        report,
        f'metric_status.{metric.status.value}',
        metric.status.value.replace('_', ' ').title(),
    )


def _format_metric(metric: Metric, kind: str) -> str:
    if metric.value is None:
        return 'N/A'
    value = metric.value
    if kind == 'currency':
        if isinstance(value, Money):
            return value.currency.format_amount(value.value, 'formal', 2)
        return f'{float(value):,.2f}'
    if kind == 'percent':
        return f'{float(Percentage.from_fraction(value)):.3f}%'
    if kind == 'multiple':
        return f'{float(value):.2f}x'
    if kind == 'integer':
        return f'{int(float(value)):,}'
    return f'{float(value):,.2f}'


def _metric_card(report: Report, spec: Any) -> str:
    metric: Metric = getattr(getattr(report.analysis, spec.section), spec.field)
    title = _analyzer_translation(report, spec.mnemonic, spec.fallback)
    status = _status_text(report, metric)
    status_key = metric.status.value
    return (
        f'<article class="metric-card" data-metric-card '
        f'data-metric-status="{escape(status_key, quote=True)}" '
        f'style="--status:{_status_color(metric)}">'
        '<div class="metric-card-top">'
        f'<div class="metric-label">{escape(title)}</div>'
        f'<span class="metric-status" title="{escape(status, quote=True)}">'
        f'{escape(status)}</span></div>'
        f'<div class="metric-value">{escape(_format_metric(metric, spec.kind))}</div>'
        '</article>'
    )


def _section(
    report: Report,
    title: str,
    body: str,
    description: str = '',
    *,
    actions: str = '',
    attributes: str = '',
) -> str:
    section_attributes = f' {attributes}' if attributes else ''
    return (
        f'<section class="section"{section_attributes}>'
        '<div class="section-heading">'
        f'<div><h2>{escape(title)}</h2><p>{escape(description)}</p></div>'
        f'{actions}</div>'
        f'{body}</section>'
    )


def _summary(report: Report) -> str:
    descriptive = report.analysis.descriptive_facts
    quantifiable = report.analysis.quantifiable_facts
    price = quantifiable.price
    delta = float(price.delta_pct) if price.delta_pct is not None else None
    delta_text = (
        f'{"+" if delta is not None and delta > 0 else ""}{delta:.3f}% '
        f'{_ui(report, "summary.vs_prior_period", "vs. prior period")}'
        if delta is not None
        else _ui(report, 'summary.change_unavailable', 'Change unavailable')
    )
    cards = [
        ('summary.open', _safe(descriptive.open), 'summary.open_context'),
        ('summary.high', _safe(descriptive.high), 'summary.high_context'),
        ('summary.low', _safe(descriptive.low), 'summary.low_context'),
        ('summary.close', _safe(descriptive.close), 'summary.close_context'),
    ]
    cards_html = ''.join(
        f'<article class="panel stat-card"><div class="stat-label">'
        f'{escape(_ui(report, key, key))}</div><div class="stat-value">'
        f'{escape(value)}</div><div class="stat-note">'
        f'{escape(_ui(report, note, note))}</div></article>'
        for key, value, note in cards
    )
    title = _first_text(descriptive.formal_name, descriptive.name)
    price_class = 'positive' if delta is None or delta >= 0 else 'negative'
    profile = _profile(report)
    return (
        f'<div class="instrument-bar"><div class="instrument-mark" data-fallback="{escape(report.ticker.symbol[:4], quote=True)}">'
        f'<img src="{escape(Theme.GBM_SYMBOL_LOGO_URL.format(symbol=report.ticker.symbol), quote=True)}" '
        f'alt="{escape(title)} logo" loading="lazy" '
        'onerror="this.style.display=\'none\';this.parentElement.classList.add(\'instrument-mark-missing\');">'
        '</div>'
        f'<div><div class="instrument-name">{escape(report.ticker.ticker)}</div>'
        f'<div class="instrument-subtitle">{escape(title)} · {escape(_quote_type(report))}</div></div></div>'
        '<div class="layout"><div class="main-column">'
        '<article class="panel price-panel">'
        f'<div class="eyebrow">{escape(_ui(report, "summary.eyebrow", "INVESTMENT BRIEF"))}</div>'
        f'<h1>{escape(_ui(report, "summary.current_price", "Current price"))}</h1>'
        f'<span class="price">{escape(_format_metric(price, "currency"))}</span>'
        f'<span class="price-unit">{escape(_safe(descriptive.currency))}</span>'
        f'<div class="change {price_class}">{escape(delta_text)}</div>'
        '</article>'
        f'<section class="cards">{cards_html}</section>'
        f'{_section(report, _ui(report, "summary.company_profile", "Company profile"), profile)}'
        '</div><aside class="side-column"><article class="panel market-access-panel">'
        f'<div class="eyebrow">{escape(_ui(report, "html.market_access", "Market access"))}</div>'
        f'<h2>{escape(_quote_type(report))}</h2>'
        f'<p class="muted">{escape(_ui(report, "html.market_access_note", "Open the live market pages for this instrument."))}</p>'
        '<div class="market-links">'
        f'<a class="market-link" href="{escape(Theme.GBM_URL.format(symbol=report.ticker.symbol), quote=True)}" target="_blank" rel="noreferrer">'
        '<span><strong>GBM</strong><small>Live market page</small></span><span class="market-link-arrow" aria-hidden="true">&rarr;</span></a>'
        f'<a class="market-link" href="{escape(Theme.TRADINGVIEW_URL.format(symbol=report.ticker.symbol), quote=True)}" target="_blank" rel="noreferrer">'
        '<span><strong>TradingView</strong><small>Charts and price action</small></span><span class="market-link-arrow" aria-hidden="true">&rarr;</span></a>'
        '</div></article>'
        '<article class="panel"><div class="eyebrow">Instrument snapshot</div>'
        f'<h2>{escape(title)}</h2><div class="aside-facts">'
        f'<div class="aside-fact"><span>Sector</span><strong>{escape(_safe(descriptive.sector))}</strong></div>'
        f'<div class="aside-fact"><span>Industry</span><strong>{escape(_safe(descriptive.industry))}</strong></div>'
        f'<div class="aside-fact"><span>Currency</span><strong>{escape(_safe(descriptive.currency))}</strong></div>'
        '</div></article></aside></div>'
    )


def _profile(report: Report) -> str:
    descriptive = report.analysis.descriptive_facts
    rows = [
        ('details.company', _first_text(descriptive.formal_name, descriptive.name)),
        ('details.ticker', report.ticker.ticker),
        ('details.region', report.ticker.region),
        ('details.currency', _safe(descriptive.currency)),
        ('details.sector', _safe(descriptive.sector)),
        ('details.industry', _safe(descriptive.industry)),
        ('details.address', _safe(descriptive.address)),
        ('details.quote_type', _quote_type(report)),
        ('details.website', _safe(descriptive.website)),
        ('details.phone', _safe(descriptive.phone)),
    ]
    return '<div class="panel profile">' + ''.join(
        f'<div class="profile-row"><strong>{escape(_ui(report, key, key))}</strong>'
        f'<span>{escape(value)}</span></div>'
        for key, value in rows
    ) + '</div>'


def _analysis(report: Report, preset: ReportPreset) -> str:
    sections = [
        ('valuation', report.analysis.valuation),
        ('profitability', report.analysis.profitability),
        ('cash_flow', report.analysis.cash_flow),
        ('growth', report.analysis.growth),
        ('financial_health', report.analysis.financial_health),
        ('capital_allocation', report.analysis.capital_allocation),
        ('working_capital', report.analysis.working_capital),
    ]
    output: list[str] = []
    for section_name, model in sections:
        if section_name not in preset.sections:
            continue
        specs = [
            spec for spec in METRIC_SPECS
            if spec.section == section_name
            and _requested(report, spec.section, spec.field)
        ]
        if not specs:
            continue
        title = _analyzer_translation(
            report,
            section_name,
            section_name.replace('_', ' ').title(),
        )
        description = _analyzer_translation(
            report,
            section_name,
            '',
            field='description',
        )
        cards = ''.join(_metric_card(report, spec) for spec in specs)
        output.append(_section(
            report,
            title,
            f'<div class="metric-grid">{cards}</div>'
            f'<div class="metric-empty" data-metric-empty hidden>'
            f'{escape(_ui(report, "html.no_matching_metrics", "No metrics match this filter."))}</div>',
            description,
            actions=_metric_toolbar(report, specs),
            attributes='data-metric-section',
        ))
    return ''.join(output)


def _requested(report: Report, section: str, field: str) -> bool:
    if report.mode.value != 'custom':
        return True
    requested = {item.strip().lower() for item in report.custom_report}
    aliases = {field.lower()}
    if field == 'ev_to_market_cap':
        aliases.add('ev2market_cap')
    return section.lower() in requested or bool(requested.intersection(aliases))


def _metric_toolbar(report: Report, specs: list[Any]) -> str:
    seen_statuses: set[str] = set()
    filters = [
        (
            'all',
            _ui(report, 'html.all_metrics', 'All'),
        ),
    ]
    for spec in specs:
        metric: Metric = getattr(getattr(report.analysis, spec.section), spec.field)
        status_key = metric.status.value
        if status_key in seen_statuses:
            continue
        seen_statuses.add(status_key)
        filters.append((status_key, _status_text(report, metric)))
    buttons = ''.join(
        f'<button class="metric-filter" type="button" data-metric-filter="{escape(value, quote=True)}" '
        f'aria-pressed="{"true" if value == "all" else "false"}">{escape(label)}</button>'
        for value, label in filters
    )
    return (
        '<div class="metric-toolbar" data-metric-controls '
        f'aria-label="{escape(_ui(report, "html.filter_metrics", "Filter metrics"), quote=True)}">'
        f'<span class="metric-toolbar-label">{escape(_ui(report, "html.filter_metrics", "Filter metrics"))}</span>'
        f'{buttons}</div>'
    )


def _prediction(report: Report) -> str:
    prediction = report.prediction_result
    rows = ''.join(
        f'<div class="probability"><span>{escape(item.action.value.upper())}</span>'
        f'<div class="bar"><i style="width:{float(item.probability):.2f}%"></i></div>'
        f'<strong>{float(item.probability):.2f}%</strong></div>'
        for item in prediction.action_probabilities
    )
    body = (
        '<div class="panel prediction"><div><div class="eyebrow">'
        f'{escape(_ui(report, "prediction.model_signal", "MODEL SIGNAL"))}</div>'
        f'<div class="signal">{escape(prediction.top_action.value.upper())}</div>'
        f'<p class="muted">{escape(_ui(report, "prediction.confidence", "Confidence"))}: '
        f'{float(prediction.confidence):.2f}% · '
        f'{escape(_ui(report, "prediction.horizon", "Horizon"))}: '
        f'{prediction.horizon} {escape(prediction.horizon_unit)}</p></div>'
        f'<div class="probabilities">{rows}</div></div>'
    )
    explanation = getattr(report, 'explanation', None)
    if explanation:
        body += f'<div class="panel"><p>{escape(explanation.summary)}</p>'
        body += ''.join(
            f'<p>{escape(point.reasoning.value)} {escape(point.content)}</p>'
            for point in explanation.points
        ) + '</div>'
    return _section(
        report,
        _ui(report, 'section.prediction', 'AI Generated Prediction'),
        body,
    )


def _facts(report: Report) -> str:
    quantitative = report.analysis.quantifiable_facts
    descriptive = report.analysis.descriptive_facts
    rows = [
        ('facts.dividend_yield', _format_metric(quantitative.dividend_yield, 'percent')),
        ('facts.dividend_rate', _format_metric(quantitative.dividend_rate, 'currency')),
        ('facts.last_dividend', _safe(descriptive.last_dividend)),
        ('facts.splits', _safe(descriptive.splits)),
    ]
    body = '<div class="panel profile">' + ''.join(
        f'<div class="profile-row"><strong>{escape(_ui(report, key, key))}</strong>'
        f'<span>{escape(value)}</span></div>'
        for key, value in rows
    ) + '</div>'
    return _section(
        report,
        _ui(report, 'section.dividends_and_splits', 'Dividends and Splits'),
        body,
    )


def _widget(report: Report, range_name: str) -> str:
    config = {
        'autosize': True,
        'symbol': report.ticker.ticker,
        'interval': 'D',
        'range': range_name,
        'timezone': 'Etc/UTC',
        'theme': 'light',
        'style': '1',
        'locale': report.account.language.code,
        'enable_publishing': False,
        'hide_top_toolbar': False,
        'hide_legend': False,
        'save_image': False,
        'calendar': False,
        'support_host': Theme.TRADINGVIEW_SUPPORT_HOST,
        'compareSymbols': [{'symbol': 'SP:SPX', 'position': 'SameScale'}],
    }
    config_attr = escape(json.dumps(config, ensure_ascii=True), quote=True)
    return (
        f'<div class="tv-container tv-widget" data-tv-config="{config_attr}">'
        '<div class="tradingview-widget-container__widget"></div></div>'
    )


def _charts(report: Report) -> str:
    charts = [
        ('5y', 'chart.price_history_5y', 'chart.price_history_5y_description'),
        ('1y', 'chart.price_history_1y', 'chart.price_history_1y_description'),
        ('3m', 'chart.price_history_3mo', 'chart.price_history_3mo_description'),
        ('5d', 'chart.price_history_1w', 'chart.price_history_1w_description'),
    ]
    tabs = ''.join(
        f'<button class="chart-tab" type="button" role="tab" id="tab-{range_name}" '
        f'aria-controls="chart-{range_name}" aria-selected="{"true" if index == 0 else "false"}" '
        f'tabindex="{0 if index == 0 else -1}" data-chart-target="chart-{range_name}">'
        f'{escape(range_name.upper())}</button>'
        for index, (range_name, _, _) in enumerate(charts)
    )
    panels = ''.join(
        f'<article class="chart-card" role="tabpanel" id="chart-{range_name}" '
        f'aria-labelledby="tab-{range_name}" data-chart-panel="chart-{range_name}"'
        f'{" hidden" if index else ""}><h3>{escape(_ui(report, title, title))}</h3>'
        f'<p class="muted">{escape(_ui(report, description, ""))}</p>'
        f'{_widget(report, range_name)}</article>'
        for index, (range_name, title, description) in enumerate(charts)
    )
    body = (
        f'<div class="chart-tabs" role="tablist" data-chart-tabs '
        f'aria-label="{escape(_ui(report, "html.chart_period", "Chart period"), quote=True)}">{tabs}</div>'
        f'<div class="chart-grid">{panels}</div>'
    )
    return _section(
        report,
        _ui(report, 'section.charts', 'Market charts'),
        body,
        attributes='data-chart-section',
    )


def _news(report: Report) -> str:
    articles = list(report.news_compilation)
    if not articles:
        body = f'<div class="panel empty">{escape(_ui(report, "news.empty", "No recent news available."))}</div>'
    else:
        body = '<div class="news-list">' + ''.join(
            f'<article class="news-card"><h3>{escape(article.title)}</h3>'
            f'<div>{escape(article.summary)}</div>'
            f'<div class="muted">{escape(article.source.name or article.source.url)}'
            f' · {escape(article.published_at or "")}</div></article>'
            for article in articles
        ) + '</div>'
    return _section(
        report,
        _ui(report, 'section.recent_news', 'Recent News'),
        body,
    )


def _document(
    report: Report,
    content: str,
    *,
    title: str,
    active: str,
    site: bool,
    home_href: str,
    nav_items: list[tuple[str, str, str]] | None = None,
) -> str:
    generated_at = datetime.now()
    nav_items = nav_items or [
        ('index.html', _ui(report, 'html.overview', 'Overview'), 'overview'),
        ('analysis.html', _ui(report, 'html.analysis', 'Analysis'), 'analysis'),
        ('charts.html', _ui(report, 'section.charts', 'Market charts'), 'charts'),
        ('facts.html', _ui(report, 'html.facts', 'Facts'), 'facts'),
    ]
    nav = ''.join(
        f'<a class="{"active" if key == active else ""}" href="{escape(href)}">{escape(label)}</a>'
        for href, label, key in nav_items
    )
    stylesheet = '<link rel="stylesheet" href="src/styles.css">' if site else f'<style>{_css()}</style>'
    script = '<script defer src="src/app.js"></script>' if site else f'<script>{_JAVASCRIPT}</script>'
    font_stylesheet = escape(Theme.FONT_WEB_STYLESHEET, quote=True)
    footer = _ui(
        report,
        'footer.generated_by',
        'Report generated by {app} ~ {author}',
    ).format(app=APP_NAME_CODING, author=APP_AUTHOR)
    return (
        '<!doctype html><html lang="' + escape(report.account.language.code) + '"><head>'
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta name="generator" content="{escape(APP_NAME_CODING)}">'
        f'<meta name="author" content="{escape(APP_AUTHOR)}">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        f'<link rel="stylesheet" href="{font_stylesheet}">'
        '<script src="https://cdn.tailwindcss.com"></script>'
        f'<script>{_TAILWIND_CONFIG}</script>'
        f'<title>{escape(title)}</title>{stylesheet}</head><body>'
        '<header class="app-header sticky top-0 z-50 shadow-sm"><span class="menu-icon" aria-hidden="true">⌁</span>'
        f'<a class="brand" href="{escape(home_href)}">{escape(_ui(report, "app.name", APP_NAME))}</a>'
        f'<span class="brand-badge">{escape(_ui(report, "html.research", "Research"))}</span>'
        '<nav class="global-nav">'
        f'{nav}</nav><span class="header-meta">'
        f'{escape(report.ticker.ticker)} · {escape(_quote_type(report))}</span></header>'
        f'<main class="shell mx-auto">{content}</main><footer class="footer">'
        f'<span>{escape(footer)}</span><time datetime="{generated_at.isoformat()}">'
        f'{escape(generated_at.strftime("%Y-%m-%d %H:%M"))}</time></footer>{script}'
        '</body></html>'
    )


class HTMLPageRenderer:
    """Render a complete responsive report into one self-contained HTML file."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs

    def render(self, report: Report, output: str | None = None) -> None:
        destination = normalize_output(output, report, 'html')
        path = Path(destination or f'{report.ticker.symbol.lower()}_report.html')
        path.parent.mkdir(parents=True, exist_ok=True)
        preset = get_preset(report.mode)
        content = _summary(report)
        if preset.show_explanation and _feature_requested(report, 'explanation'):
            content += _prediction(report)
        if preset.show_analysis:
            content += _analysis(report, preset)
        if preset.show_facts and _feature_requested(report, 'dividends_and_splits'):
            content += _facts(report)
        if preset.show_news:
            content += _news(report)
        content += _charts(report)
        path.write_text(
            _document(
                report,
                content,
                title=f'{report.ticker.ticker} report',
                active='overview',
                site=False,
                home_href='#',
                nav_items=[
                    ('#', _ui(report, 'html.full_report', 'Report'), 'overview'),
                ],
            ),
            encoding='utf-8',
        )


def _feature_requested(report: Report, feature: str) -> bool:
    if report.mode.value != 'custom':
        return True
    requested = {item.strip().lower() for item in report.custom_report}
    if feature == 'dividends_and_splits':
        return bool(requested.intersection({'dividends_and_splits', 'dividends', 'splits'}))
    return feature in requested


class HTMLSiteRenderer:
    """Render a static, Astro-like vanilla site with shared CSS and JavaScript."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs

    def normalize_output(self, report: Report, output: str | None = None) -> Path:
        destination: str | None = normalize_output(output, report, 'html-site')
        root: Path = Path(destination or f'{report.ticker.symbol.lower()}_report_site')
        if root.suffix.lower() in {'.html', '.htm', '.site'}:
            root = root.with_suffix('')
        return root

    def render(self, report: Report, output: str | None = None) -> None:
        root: Path = self.normalize_output(report, output)
        root.mkdir(parents=True, exist_ok=True)
        assets: Path = root / 'src'
        assets.mkdir(parents=True, exist_ok=True)
        (assets / 'styles.css').write_text(_css(), encoding='utf-8')
        (assets / 'app.js').write_text(_JAVASCRIPT, encoding='utf-8')

        preset: ReportPreset = get_preset(report.mode)
        pages: list[tuple[str, str, str, str]] = [
            ('index.html', _ui(report, 'html.overview', 'Overview'), _summary(report), 'overview'),
            ('charts.html', _ui(report, 'section.charts', 'Market charts'), _charts(report), 'charts'),
        ]
        if preset.show_analysis:
            pages.insert(
                1,
                ('analysis.html', _ui(report, 'html.analysis', 'Analysis'), _analysis(report, preset), 'analysis'),
            )
        if preset.show_facts and _feature_requested(report, 'dividends_and_splits'):
            pages.append(
                ('facts.html', _ui(report, 'html.facts', 'Facts'), _facts(report), 'facts'),
            )
        if preset.show_explanation and _feature_requested(report, 'explanation'):
            pages.append(
                ('prediction.html', _ui(report, 'section.prediction', 'AI Generated Prediction'), _prediction(report), 'prediction'),
            )
        if preset.show_news:
            pages.append(
                ('news.html', _ui(report, 'section.recent_news', 'Recent News'), _news(report), 'news'),
            )

        for filename, page_title, body, active in pages:
            (root / filename).write_text(
                _document(
                    report,
                    body,
                    title=f'{report.ticker.ticker} · {page_title}',
                    active=active,
                    site=True,
                    home_href='index.html',
                    nav_items=[
                        (name, label, key)
                        for name, label, _, key in pages
                    ],
                ),
                encoding='utf-8',
            )
