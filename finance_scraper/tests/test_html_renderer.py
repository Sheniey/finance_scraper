# ================================================== #
# MODULE: test_html_renderer
# ================================================== #

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from finance.renderers.html.renderer import HTMLPageRenderer, HTMLSiteRenderer
from finance.services.stock_analyzer.models import Metric, MetricGrade
from datatypes import Language, ReportMode


class HTMLRendererTests(unittest.TestCase):
    def _report(self) -> SimpleNamespace:
        language = Language(code='en', name='English')
        price = Metric(metric=123.45, rating=(MetricGrade.GOOD, 'Positive session'))
        price.comparison = (MetricGrade.GOOD, 0.75, 0.006)
        analysis = SimpleNamespace(
            descriptive_facts=SimpleNamespace(
                formal_name='Example Incorporated',
                name='Example',
                quote_type='equity',
                open='122.50',
                high='125.00',
                low='121.80',
                close='123.45',
                currency='USD',
                sector='Technology',
                industry='Software',
                address='1 Example Way',
                website='https://example.test',
                phone='+1 555 0100',
                last_dividend='N/A',
                splits='N/A',
            ),
            quantifiable_facts=SimpleNamespace(price=price),
            valuation=SimpleNamespace(
                pe_ratio=Metric(
                    metric=20.3,
                    rating=(MetricGrade.GOOD, 'Attractive'),
                ),
                peg_ratio=Metric(metric=None),
            ),
            profitability=SimpleNamespace(),
            cash_flow=SimpleNamespace(),
            growth=SimpleNamespace(),
            financial_health=SimpleNamespace(),
            capital_allocation=SimpleNamespace(),
            working_capital=SimpleNamespace(),
        )
        return SimpleNamespace(
            account=SimpleNamespace(
                name='Validation user',
                email='validation@example.test',
                language=language,
            ),
            ticker=SimpleNamespace(ticker='TEST', symbol='TEST', region='US'),
            analysis=analysis,
            mode=ReportMode.CUSTOM,
            custom_report=['pe_ratio', 'peg_ratio'],
            news_compilation=[],
        )

    def test_page_embeds_assets_and_interactive_controls(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / 'report.html'
            HTMLPageRenderer().render(self._report(), str(output))
            document = output.read_text(encoding='utf-8')

        self.assertIn('<style>', document)
        self.assertIn('initializeMetricFilters', document)
        self.assertIn('data-chart-tabs', document)
        self.assertIn('data-metric-filter', document)
        self.assertIn('metric-status::before', document)
        self.assertNotIn('border-left: 4px solid', document)
        self.assertNotIn('src/styles.css', document)
        self.assertLess(
            document.index('https://cdn.tailwindcss.com'),
            document.index('tailwind.config'),
        )

    def test_site_writes_shared_css_and_javascript_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / 'report-site'
            HTMLSiteRenderer().render(self._report(), str(output))

            index = (output / 'index.html').read_text(encoding='utf-8')
            analysis = (output / 'analysis.html').read_text(encoding='utf-8')
            styles = (output / 'src' / 'styles.css').read_text(encoding='utf-8')
            script = (output / 'src' / 'app.js').read_text(encoding='utf-8')

        self.assertIn('src/styles.css', index)
        self.assertIn('src/app.js', index)
        self.assertIn('https://cdn.gbm.com/instruments/logo/TEST', index)
        self.assertIn('instrument-mark-missing', index)
        self.assertIn('data-fallback="TEST"', index)
        self.assertIn('market-link', index)
        self.assertIn('aside-facts', index)
        self.assertEqual(index.count('class="global-nav"'), 1)
        self.assertNotIn('class="site-nav"', index)
        self.assertIn('data-metric-filter', analysis)
        self.assertIn('--font-display', styles)
        self.assertIn('metric-status::before', styles)
        self.assertIn('initializeMetricFilters', script)
        self.assertIn('initializeCharts', script)


if __name__ == '__main__':
    unittest.main()
