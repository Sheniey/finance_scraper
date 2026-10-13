from datatypes.ticker import YFinanceTickerInfo
from finance.services.stock_analyzer.repository import _analysis_cache_identity
from finance.types.language import Language


def test_stock_analysis_cache_identity_includes_language_and_region() -> None:
    us_ticker: YFinanceTickerInfo = YFinanceTickerInfo(
        symbol='AAPL',
        region='US',
    )
    mexico_ticker: YFinanceTickerInfo = YFinanceTickerInfo(
        symbol='AAPL',
        region='MX',
    )
    english: Language = Language(
        code='en',
        name='English',
        style='professional',
    )
    spanish: Language = Language(
        code='es',
        name='Español',
        style='friendly',
    )
    friendly_english: Language = Language(
        code='en',
        name='English',
        style='friendly',
    )

    english_us_key, _ = _analysis_cache_identity(us_ticker, english)
    spanish_us_key, _ = _analysis_cache_identity(us_ticker, spanish)
    friendly_us_key, _ = _analysis_cache_identity(
        us_ticker,
        friendly_english,
    )
    english_mx_key, _ = _analysis_cache_identity(mexico_ticker, english)

    assert english_us_key != spanish_us_key
    assert english_us_key != friendly_us_key
    assert english_us_key != english_mx_key
