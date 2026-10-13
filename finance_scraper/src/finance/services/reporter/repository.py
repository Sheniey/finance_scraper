
import asyncio
import hashlib
import json
import logging
from typing import Any
from designkit.behavioral.typing import Assertion
from designkit.behavioral.verboser import VerboseSystem
from pydantic import ValidationError

from datatypes import Ticker
from finance.logging import (
    ACCOUNT_SERVICE_ERROR,
    ANALYZING_TICKER,
    EXPLANATION_DEGRADED,
    EXPLANATION_GENERATED,
    FETCHING_LATEST_NEWS,
    GENERATING_EXPLANATION,
    LOADING_ACCOUNT_PREFERENCES,
    ML_PREDICTION_ERROR,
    NEWS_EXTRACTOR_ERROR,
    PREDICTING_BEST_ACTION,
    REPORT_CONFIGURATION_ERROR,
    STOCK_ANALYZER_ERROR,
    EMPTY_LLM_EXPLANATION,
    INVALID_LLM_EXPLANATION,
    INVALID_LLM_PROMPT,
    INVALID_PROVIDER_PRIORITY,
    LLM_INITIALIZATION_FAILED,
    LLM_IS_UNAVAILABLE,
    LLM_PROVIDER_ERROR,
)
from finance.types import ReportMode, Language
from finance.types.report import Report
from finance.services.reporter.logging import __verboser__, NEWS_FETCHED
from finance.services.reporter.observer import ReportObserver
from finance.services.account import Account, has_positive_position
from finance.services.account.exceptions import AccountException
from finance.services.report_store.cache import cache as report_cache
from finance.services.stock_analyzer import StockAnalysis, analyze_stock, definitions as defs
from finance.services.stock_analyzer.exceptions import StockAnalyzerException
from finance.services.news_extractor import NewsCompilation, fetch_news
from finance.services.news_extractor.exceptions import NewsExtractorException
from finance.services.ml import Actions, PredictionResult, predict_share
from finance.services.ml.exceptions import ModelException as MLServiceException
from nexis.errors import ModelException as MLPipelineException
from finance.services.i18n.exceptions import I18nException
from finance.services.yf_extractor.exceptions import YFExtractorException
from finance.services.llm import (
    Explanation, ExplanationConfig, explain_action, LLMException,
    LLMInitializationError, LLMProviderError, LLMUnavailableError,
    InvalidExplanationError, InvalidPromptError, InvalidProviderPriorityError,
    EmptyExplanationError
)
from finance.types.report_presets import (
    CUSTOM_FEATURE_NAMES,
    CUSTOM_GRAPH_NAMES,
    CUSTOM_METRIC_NAMES,
)
from finance.services.reporter.exceptions import (
    InvalidCustomReportError,
    InvalidReportHorizonError,
    InvalidReportModeError,
)

_REPORT_CACHE_NAMESPACE: str = 'financial_report'
_REPORT_CACHE_TTL_SECONDS: int = 3600
_REPORT_CACHE_VERSION: int = 1
logger: logging.Logger = logging.getLogger(__name__)


# ================================================== #
# HELPER FUNCTIONS                                   #
# ================================================== #

def _resolve_mode(mode: ReportMode | str) -> ReportMode:
    if isinstance(mode, ReportMode):
        return mode
    try:
        return ReportMode(str(mode).lower())
    except ValueError as e:
        raise InvalidReportModeError(mode) from e


def _normalize_custom_report(account: Account, mode: ReportMode) -> set[str]:
    custom_report: list[str] = list(account.custom_report)
    if mode == ReportMode.CUSTOM and not custom_report:
        raise InvalidCustomReportError(
            'The custom report mode requires at least one metric in account.custom_report.'
        )

    normalized_custom_report: set[str] = {
        item.strip().lower()
        for item in custom_report
    }
    unknown_metrics = normalized_custom_report - (
        CUSTOM_METRIC_NAMES | CUSTOM_FEATURE_NAMES | CUSTOM_GRAPH_NAMES
    )
    if mode == ReportMode.CUSTOM and unknown_metrics:
        unknown_metrics_text: str = ', '.join(sorted(unknown_metrics))
        raise InvalidCustomReportError(
            f'Unknown custom report metrics: {unknown_metrics_text}.',
            tuple(sorted(unknown_metrics)),
        )
    return normalized_custom_report


def _should_generate_explanation(
    mode: ReportMode,
    normalized_custom_report: set[str],
    generate_explanation: bool,
) -> bool:
    if mode == ReportMode.INFO:
        return False
    if mode != ReportMode.CUSTOM:
        return generate_explanation
    return 'explanation' in normalized_custom_report


def _build_analysis(ticker: Ticker, language: Language) -> StockAnalysis:
    try:
        defs.load_definitions()
        with __verboser__.info_status(ANALYZING_TICKER.format(ticker=ticker.ticker)):
            return analyze_stock(ticker.dump(), language=language)
    except (
        StockAnalyzerException,
        I18nException,
        YFExtractorException,
        KeyError,
        TypeError,
        ValueError,
        OSError,
    ) as e:
        __verboser__.error(
            STOCK_ANALYZER_ERROR.format(ticker=ticker.ticker),
            expt=e,
        )
        raise

def _build_news(ticker: Ticker, max_news: int = 10) -> NewsCompilation:
    try:
        with __verboser__.info_status(FETCHING_LATEST_NEWS.format(ticker=ticker.ticker)):
            news = fetch_news(ticker.extract_data(), max_news=max_news)
            __verboser__.debug(NEWS_FETCHED.format(fetched_count=len(news), ticker=ticker.ticker))
            return news
    except (NewsExtractorException, KeyError, TypeError, ValueError) as e:
        __verboser__.error(
            NEWS_EXTRACTOR_ERROR.format(ticker=ticker.ticker),
            expt=e,
        )
        raise

def _get_language(account: Account) -> Language:
    try:
        with __verboser__.info_status(LOADING_ACCOUNT_PREFERENCES.format(account=account.email)):
            return account.language
    except (AccountException, KeyError, TypeError, ValueError) as e:
        __verboser__.error(ACCOUNT_SERVICE_ERROR, expt=e)
        raise

def _has_shares(account: Account, ticker: Ticker) -> bool:
    try:
        return has_positive_position(account, ticker)
    except (AccountException, KeyError, TypeError, ValueError) as e:
        __verboser__.error(ACCOUNT_SERVICE_ERROR, expt=e)
        raise


def _build_report_cache_key(
    account: Account,
    ticker: Ticker,
    *,
    normalized_custom_report: set[str],
    selected_mode: ReportMode,
    should_explain: bool,
    generate_charts: bool,
    horizon: int,
    has_shares: bool,
) -> str | None:
    if has_shares:
        return None
    cache_options: dict[str, Any] = {
        'version': _REPORT_CACHE_VERSION,
        'ticker': ticker.ticker,
        'language': account.language.model_dump(mode='json'),
        'mode': selected_mode.value,
        'custom_report': sorted(normalized_custom_report),
        'explain': should_explain,
        'charts': generate_charts,
        'ml_horizon': horizon,
    }
    if should_explain:
        cache_options['account_name'] = account.name
    serialized_options: str = json.dumps(
        cache_options,
        ensure_ascii=False,
        separators=(',', ':'),
        sort_keys=True,
    )
    return hashlib.sha256(serialized_options.encode('utf-8')).hexdigest()


def get_report_cache_key(
    account: Account,
    ticker: Ticker,
    *,
    generate_explanation: bool = True,
    generate_charts: bool = True,
    mode: ReportMode | str = ReportMode.CLASSIC,
    horizon: int = 10,
) -> str | None:
    Assertion(account).must_be(Account, TypeError(f'Account {account!r} must be an instance of Account'))
    Assertion(ticker).must_be(Ticker, TypeError(f'Ticker {ticker!r} must be an instance of Ticker'))
    if horizon <= 0:
        raise InvalidReportHorizonError(horizon)
    selected_mode: ReportMode = _resolve_mode(mode)
    normalized_custom_report: set[str] = _normalize_custom_report(
        account,
        selected_mode,
    )
    should_explain: bool = _should_generate_explanation(
        selected_mode,
        normalized_custom_report,
        generate_explanation,
    )
    return _build_report_cache_key(
        account,
        ticker,
        normalized_custom_report=normalized_custom_report,
        selected_mode=selected_mode,
        should_explain=should_explain,
        generate_charts=generate_charts,
        horizon=horizon,
        has_shares=_has_shares(account, ticker),
    )


def _possible_actions(has_shares: bool) -> list[str]:
    actions: tuple[Actions, ...] = (
        (Actions.BUY, Actions.HOLD, Actions.SELL)
        if has_shares
        else (Actions.BUY, Actions.WAIT)
    )
    return [action.value for action in actions]

def _predict_share(
    ticker: Ticker,
    has_shares: bool,
    *,
    horizon: int = 10
) -> PredictionResult:
    try:
        with __verboser__.info_status(PREDICTING_BEST_ACTION.format(ticker=ticker.ticker)):
            return predict_share(ticker, has_shares, horizon=horizon)
    except (
        MLServiceException,
        MLPipelineException,
        KeyError,
        TypeError,
        ValueError,
        OSError,
    ) as e:
        __verboser__.error(
            ML_PREDICTION_ERROR.format(ticker=ticker.ticker),
            expt=e,
        )
        raise

async def _explain_action(explanation_config: ExplanationConfig) -> Explanation | None:
    try:
        with __verboser__.info_status(GENERATING_EXPLANATION):
            explanation: Explanation = await explain_action(explanation_config)
        __verboser__.info(EXPLANATION_GENERATED)
        return explanation
    except LLMInitializationError as e:
        __verboser__.error(LLM_INITIALIZATION_FAILED, expt=e)
    except LLMProviderError as e:
        __verboser__.error(LLM_PROVIDER_ERROR, expt=e)
    except LLMUnavailableError as e:
        __verboser__.error(LLM_IS_UNAVAILABLE, expt=e)
    except InvalidProviderPriorityError as e:
        __verboser__.error(INVALID_PROVIDER_PRIORITY, expt=e)
    except InvalidPromptError as e:
        __verboser__.error(INVALID_LLM_PROMPT, expt=e)
    except InvalidExplanationError as e:
        __verboser__.error(INVALID_LLM_EXPLANATION, expt=e)
    except EmptyExplanationError as e:
        __verboser__.error(EMPTY_LLM_EXPLANATION, expt=e)
    except LLMException as e:
        __verboser__.error(LLM_PROVIDER_ERROR, expt=e)
    __verboser__.warning(EXPLANATION_DEGRADED)
    return None


# ================================================== #
# REPORT GENERATION                                  #
# ================================================== #

async def generate_report(
    account: Account,
    ticker: Ticker,
    *,
    generate_explanation: bool = True,
    generate_charts: bool = True,
    mode: ReportMode | str = ReportMode.CLASSIC,
    horizon: int = 10,
    verbose: bool = False,
) -> Report:
    Assertion(account).must_be(Account, TypeError(f'Account {account!r} must be an instance of Account'))
    Assertion(ticker).must_be(Ticker, TypeError(f'Ticker {ticker!r} must be an instance of Ticker'))

    __verboser__.set_verbose(verbose)
    if horizon <= 0:
        error = InvalidReportHorizonError(horizon)
        __verboser__.error(REPORT_CONFIGURATION_ERROR, expt=error)
        raise error

    try:
        selected_mode: ReportMode = _resolve_mode(mode)
        normalized_custom_report = _normalize_custom_report(account, selected_mode)
    except (InvalidReportModeError, InvalidCustomReportError) as e:
        __verboser__.error(REPORT_CONFIGURATION_ERROR, expt=e)
        raise

    language: Language = _get_language(account)
    should_explain = _should_generate_explanation(
        selected_mode,
        normalized_custom_report,
        generate_explanation,
    )

    has_shares: bool = _has_shares(account, ticker)
    cache_key: str | None = _build_report_cache_key(
        account,
        ticker,
        normalized_custom_report=normalized_custom_report,
        selected_mode=selected_mode,
        should_explain=should_explain,
        generate_charts=generate_charts,
        horizon=horizon,
        has_shares=has_shares,
    )
    if cache_key is not None:
        cached_report: bytes | None = await asyncio.to_thread(
            report_cache.get,
            _REPORT_CACHE_NAMESPACE,
            cache_key,
        )
        if cached_report is not None:
            try:
                cached_payload: Any = json.loads(cached_report)
                if (
                    not isinstance(cached_payload, dict)
                    or 'account' in cached_payload
                ):
                    raise ValueError(
                        'Cached canonical report must not include an account',
                    )
                cached_payload['account'] = account.model_dump(mode='json')
                return Report.model_validate(cached_payload)
            except (TypeError, ValueError, ValidationError) as e:
                await asyncio.to_thread(
                    report_cache.delete,
                    _REPORT_CACHE_NAMESPACE,
                    cache_key,
                )
                logger.warning(
                    'Discarding invalid cached report %s: %s',
                    cache_key,
                    error,
                )

    analysis, news, prediction_result = await asyncio.gather(
        asyncio.to_thread(_build_analysis, ticker, language),
        asyncio.to_thread(_build_news, ticker),
        asyncio.to_thread(_predict_share, ticker, has_shares, horizon=horizon),
    )

    report: Report = Report(
        account=account,
        ticker=ticker,
        news_compilation=news,
        analysis=analysis,
        prediction_result=prediction_result,
        has_explanation=should_explain,
        charts=generate_charts,
        mode=selected_mode,
        custom_report=sorted(normalized_custom_report),
    )
    print('Prediction: ', report.prediction_result.model_dump_json(indent=2))

    if should_explain:
        explanation_config: ExplanationConfig = ExplanationConfig[Actions](
            action=prediction_result.top_action,
            possible_actions=_possible_actions(has_shares),
            account=account,
            ticker=ticker,
            news_compilation=news,
            analysis=analysis,
            charts=generate_charts,
            prediction_result=prediction_result,
            mode=selected_mode,
        )
        explanation: Explanation | None = await _explain_action(explanation_config)
        report.explanation = explanation

    if cache_key is not None:
        canonical_report: dict[str, Any] = report.model_dump(mode='json')
        canonical_report.pop('account', None)
        await asyncio.to_thread(
            report_cache.set,
            _REPORT_CACHE_NAMESPACE,
            cache_key,
            json.dumps(
                canonical_report,
                ensure_ascii=False,
                separators=(',', ':'),
                sort_keys=True,
            ).encode('utf-8'),
            ttl_seconds=_REPORT_CACHE_TTL_SECONDS,
        )

    return report


class ReportFacade:
    def __init__(self, observers: list[ReportObserver] | None = None) -> None:
        self.__observers: list[ReportObserver] = observers or []

    async def generate(self, *args: Any, **kwargs: Any) -> Report:
        report: Report = await generate_report(*args, **kwargs)
        for observer in self.__observers:
            observer.update(report)
        return report
