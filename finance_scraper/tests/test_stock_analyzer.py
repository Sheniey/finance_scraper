# ================================================== #
# MODULE: test_stock_analyzer
# ================================================== #

import asyncio
import unittest
from types import SimpleNamespace

import pandas as pd

from finance.renderers.console import fmt
from finance.renderers.console.renderer import _custom_feature_requested, _translation
from finance.services.account.models import Account
from finance.services.reporter.repository import generate_report
from finance.services.stock_analyzer import analyze_stock
from finance.services.i18n.i18n import load_i18n
from finance.services.yf_extractor.repository import build_info
from finance.services.stock_analyzer.models import Metric, MetricGrade
from datatypes import (
    Language,
    Money as MoneyWrapper,
    ReportMode,
    Ticker,
    YFinanceTickerInfo,
    YFinanceStatement,
    to_money,
)


class StockAnalyzerTests(unittest.TestCase):
    def test_build_info_normalizes_yahoo_data(self) -> None:
        ticker = SimpleNamespace(
            ticker='TEST',
            info={
                'symbol': 'TEST',
                'currentPrice': 10,
                'corporateActions': [
                    {
                        'meta': {
                            'eventType': 'DIVIDEND',
                            'amount': '0.53',
                        }
                    }
                ],
            },
            history=lambda **_: pd.DataFrame(
                {'Close': [9.0], 'Adj Close': [8.5], 'Volume': [100]},
                index=pd.to_datetime(['2025-01-01']),
            ),
            actions=pd.DataFrame(
                {'Dividends': [0.2, 0.0], 'Stock Splits': [0.0, 2.0]},
                index=pd.to_datetime(['2024-01-01', '2025-01-01']),
            ),
            financials=pd.DataFrame(
                {'2024-12-31': [100.0]},
                index=['Total Revenue'],
            ),
            balance_sheet=pd.DataFrame(
                {'2024-12-31': [80.0]},
                index=['Total Assets'],
            ),
            cashflow=pd.DataFrame(
                {'2024-12-31': [60.0]},
                index=['Operating Cash Flow'],
            ),
        )

        info = build_info(ticker)

        self.assertEqual(info.history[0].close, 9.0)
        self.assertEqual(info.dividendHistory[0].amount, 0.2)
        self.assertEqual(info.splitHistory[0].ratio, 2.0)
        self.assertEqual(
            info.incomeStatement.values['Total Revenue']['2024-12-31'],
            100.0,
        )

    def test_derived_metrics_use_statements(self) -> None:
        info = YFinanceTickerInfo(
            symbol='TEST',
            currentPrice=100,
            marketCap=1_000_000,
            enterpriseValue=1_100_000,
            enterpriseToEbitda=8,
            freeCashflow=90_000,
            operatingCashflow=120_000,
            totalDebt=100_000,
            totalCash=50_000,
            totalRevenue=500_000,
            incomeStatement=YFinanceStatement(
                values={
                    'Operating Income': {'2024-12-31': 100_000},
                    'Pretax Income': {'2024-12-31': 95_000},
                    'Tax Provision': {'2024-12-31': 19_000},
                }
            ),
            balanceSheet=YFinanceStatement(
                values={
                    'Stockholders Equity': {'2024-12-31': 300_000},
                    'Current Assets': {'2024-12-31': 200_000},
                    'Current Liabilities': {'2024-12-31': 110_000},
                }
            ),
        )

        analysis = analyze_stock(info)

        self.assertIsInstance(analysis.quantifiable_facts.price.value, MoneyWrapper)
        self.assertEqual(analysis.quantifiable_facts.price.value.currency.code, 'USD')
        self.assertIsInstance(analysis.cash_flow.owner_earnings.value, MoneyWrapper)
        self.assertAlmostEqual(analysis.valuation.price_to_fcf.value, 1000000 / 90000)
        self.assertAlmostEqual(float(analysis.cash_flow.owner_earnings.value), 90000)
        self.assertAlmostEqual(float(analysis.financial_health.net_debt.value), 50000)
        self.assertAlmostEqual(analysis.profitability.roic.value, 0.2285714285)

    def test_percent_formatter_does_not_mutate_metric(self) -> None:
        metric = Metric(metric=0.25, rating=(MetricGrade.GOOD, 'Good'))

        formatted = fmt.as_percent(metric)

        self.assertIn('25.000%', formatted)
        self.assertEqual(metric.metric, 0.25)

    def test_nan_is_rendered_as_missing(self) -> None:
        metric = Metric(metric=float('nan'))

        self.assertIsNone(metric.value)
        self.assertEqual(fmt.as_percent(metric), '[dim]N/A[/dim]')

    def test_yahoo_dividend_yield_percentage_is_normalized(self) -> None:
        analysis = analyze_stock(
            YFinanceTickerInfo(
                symbol='YIELD_TEST',
                dividendYield=1.78,
                fiveYearAvgDividendYield=1.40,
            )
        )

        self.assertAlmostEqual(analysis.quantifiable_facts.dividend_yield.value, 0.0178)
        self.assertNotIn('178.000%', fmt.as_percent(analysis.quantifiable_facts.dividend_yield))

    def test_money_values_receive_a_non_neutral_color(self) -> None:
        analysis = analyze_stock(
            YFinanceTickerInfo(
                symbol='MONEY_TEST',
                currency='MXN',
                financialCurrency='MXN',
                currentPrice=100,
                freeCashflow=1000,
            )
        )

        rendered = fmt.as_currency(analysis.financial_health.free_cash_flow)

        self.assertNotIn('[dim]', rendered)
        self.assertIn('MXN', rendered)

    def test_console_uses_account_language_for_metric_titles(self) -> None:
        language = Language(code='es', name='Spanish')
        load_i18n(language)
        report = SimpleNamespace(account=SimpleNamespace(language=language))

        self.assertEqual(
            _translation(
                report,
                'capital_allocation.shares_outstanding',
                'Shares Outstanding',
            ),
            'Acciones en Circulación',
        )
        self.assertEqual(
            _translation(report, 'financial_health.net_debt', 'Net Debt'),
            'Deuda Neta',
        )

    def test_custom_features_are_opt_in(self) -> None:
        report = SimpleNamespace(
            mode=ReportMode.CUSTOM,
            custom_report=['pe_ratio'],
        )

        self.assertFalse(_custom_feature_requested(report, 'explanation'))
        self.assertFalse(_custom_feature_requested(report, 'dividends_and_splits'))

        report.custom_report.append('explanation')
        report.custom_report.append('splits')

        self.assertTrue(_custom_feature_requested(report, 'explanation'))
        self.assertTrue(_custom_feature_requested(report, 'dividends_and_splits'))

    def test_to_money_detects_currency_symbol(self) -> None:
        money = to_money('€123.45')

        self.assertIsNotNone(money)
        self.assertEqual(money.currency.code, 'EUR')
        self.assertAlmostEqual(float(money), 123.45)

    def test_generate_report_rejects_unknown_custom_metric(self) -> None:
        account = Account(
            name='Tester',
            email='tester@example.com',
            custom_report=['unknown_metric'],
        )

        with self.assertRaisesRegex(ValueError, 'Unknown custom report metrics'):
            asyncio.run(
                generate_report(
                    account,
                    Ticker(ticker='AAPL'),
                    mode=ReportMode.CUSTOM,
                )
            )


if __name__ == '__main__':
    unittest.main()
