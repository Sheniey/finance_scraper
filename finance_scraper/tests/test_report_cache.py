import asyncio
import json
from typing import Any

from datatypes.ticker import Ticker
from finance.services.account.models import Action, Account, Stock
from finance.types.report_mode import ReportMode
from finance.services.reporter import repository as ReportRepository


class MemoryReportCache:
    def __init__(self) -> None:
        self.entries: dict[tuple[str, str], bytes] = {}

    def get(self, namespace: str, key: str) -> bytes | None:
        return self.entries.get((namespace, key))

    def set(
        self,
        namespace: str,
        key: str,
        value: bytes,
        *,
        ttl_seconds: int,
    ) -> None:
        assert ttl_seconds == 3600
        self.entries[(namespace, key)] = value

    def delete(self, namespace: str, key: str) -> bool:
        return self.entries.pop((namespace, key), None) is not None


class FakePrediction:
    def model_dump_json(self, *, indent: int) -> str:
        return '{}'


class FakeReport:
    def __init__(self, **values: Any) -> None:
        self.__dict__.update(values)
        self.prediction_result = values.get(
            'prediction_result',
            FakePrediction(),
        )

    def model_dump(self, *, mode: str) -> dict[str, Any]:
        account: Any = self.account
        if isinstance(account, Account):
            account = account.model_dump(mode=mode)
        return {
            'account': account,
            'ticker': {'ticker': self.ticker.ticker},
            'analysis': {'value': 'canonical'},
        }

    @classmethod
    def model_validate(cls, values: dict[str, Any]) -> 'FakeReport':
        report: FakeReport = cls(
            account=values['account'],
            ticker=Ticker(ticker=values['ticker']['ticker']),
            analysis=values['analysis'],
        )
        report.prediction_result = FakePrediction()
        return report


def _account(
    name: str,
    email: str,
    *,
    portfolio: list[Stock] | None = None,
) -> Account:
    return Account(
        name=name,
        email=email,
        portfolio=portfolio or [],
    )


def test_report_cache_key_includes_preferences_and_account_name_for_explanations() -> None:
    ticker: Ticker = Ticker(ticker='AAPL.US')
    first: Account = _account('First User', 'first@example.com')
    second: Account = _account('Second User', 'second@example.com')
    options: dict[str, Any] = {
        'generate_charts': True,
        'mode': ReportMode.CLASSIC,
        'horizon': 15,
    }

    first_key: str | None = ReportRepository.get_report_cache_key(
        first,
        ticker,
        generate_explanation=False,
        **options,
    )
    second_key: str | None = ReportRepository.get_report_cache_key(
        second,
        ticker,
        generate_explanation=False,
        **options,
    )
    first_explained_key: str | None = ReportRepository.get_report_cache_key(
        first,
        ticker,
        generate_explanation=True,
        **options,
    )
    second_explained_key: str | None = ReportRepository.get_report_cache_key(
        second,
        ticker,
        generate_explanation=True,
        **options,
    )
    different_horizon_key: str | None = ReportRepository.get_report_cache_key(
        second,
        ticker,
        generate_explanation=False,
        **(options | {'horizon': 30}),
    )

    assert first_key is not None
    assert first_key == second_key
    assert first_explained_key != second_explained_key
    assert second_key != different_horizon_key


def test_positive_holdings_bypass_cache_only_for_matching_ticker_region() -> None:
    ticker: Ticker = Ticker(ticker='AAPL.US')
    options: dict[str, Any] = {
        'generate_explanation': False,
        'generate_charts': True,
        'mode': ReportMode.CLASSIC,
        'horizon': 15,
    }
    us_position: Stock = Stock(
        ticker='AAPL',
        region='USD',
        currency='USD',
        actions=[Action(action='BUY', quantity=1, price=100, date='2026-01-01')],
    )
    mx_position: Stock = Stock(
        ticker='AAPL',
        region='MX',
        currency='MXN',
        actions=[Action(action='BUY', quantity=1, price=100, date='2026-01-01')],
    )
    sold_position: Stock = Stock(
        ticker='AAPL',
        region='US',
        currency='USD',
        actions=[
            Action(action='BUY', quantity=1, price=100, date='2026-01-01'),
            Action(action='SELL', quantity=1, price=100, date='2026-01-02'),
        ],
    )

    assert ReportRepository.get_report_cache_key(
        _account('US holder', 'us@example.com', portfolio=[us_position]),
        ticker,
        **options,
    ) is None
    assert ReportRepository.get_report_cache_key(
        _account('MX holder', 'mx@example.com', portfolio=[mx_position]),
        ticker,
        **options,
    ) is not None
    assert ReportRepository.get_report_cache_key(
        _account('Former holder', 'former@example.com', portfolio=[sold_position]),
        ticker,
        **options,
    ) is not None


def test_cached_report_is_canonical_and_rehydrated_for_requesting_account(
    monkeypatch,
) -> None:
    cache: MemoryReportCache = MemoryReportCache()
    analysis_calls: int = 0

    def build_analysis(ticker: Ticker, language: object) -> object:
        nonlocal analysis_calls
        analysis_calls += 1
        return object()

    monkeypatch.setattr(ReportRepository, 'report_cache', cache)
    monkeypatch.setattr(ReportRepository, 'Report', FakeReport)
    monkeypatch.setattr(ReportRepository, '_build_analysis', build_analysis)
    monkeypatch.setattr(
        ReportRepository,
        '_build_news',
        lambda ticker: object(),
    )
    monkeypatch.setattr(
        ReportRepository,
        '_predict_share',
        lambda ticker, has_shares, *, horizon: FakePrediction(),
    )
    first_account: Account = _account('First User', 'first@example.com')
    second_account: Account = _account('Second User', 'second@example.com')
    ticker: Ticker = Ticker(ticker='AAPL.US')

    async def generate() -> tuple[FakeReport, FakeReport]:
        first_report: FakeReport = await ReportRepository.generate_report(
            first_account,
            ticker,
            generate_explanation=False,
            mode=ReportMode.CLASSIC,
        )
        second_report: FakeReport = await ReportRepository.generate_report(
            second_account,
            ticker,
            generate_explanation=False,
            mode=ReportMode.CLASSIC,
        )
        return first_report, second_report

    first_report, second_report = asyncio.run(generate())
    cached_payload: bytes = next(iter(cache.entries.values()))
    cached_data: dict[str, Any] = json.loads(cached_payload)

    assert first_report.account is first_account
    assert second_report.account['email'] == 'second@example.com'
    assert analysis_calls == 1
    assert 'account' not in cached_data
    assert 'first@example.com' not in cached_payload.decode('utf-8')
    assert 'Second User' not in cached_payload.decode('utf-8')
