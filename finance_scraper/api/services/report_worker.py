import asyncio
import logging
import time
from asyncio import FIRST_COMPLETED, Task
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from datatypes.ticker import Ticker
from finance.renderers import smart_render_strategy
from finance.services.account import get_by_id
from finance.services.llm.exceptions import LLMException, OllamaNotInstalledError
from finance.services.ml.exceptions import ModelException
from finance.services.report_store import cache as shared_cache
from finance.services.reporter import generate_report
from finance.services.reporter.exceptions import ReporterException
from finance.services.reporter.repository import get_report_cache_key
from finance.services.yf_extractor.exceptions import YFinanceError

from api.core.config import settings, IS_DEV
from api.models.report import ReportJob
from api.repositories import report as ReportRepository
from api.services.worker_capacity import get_report_worker_concurrency


logger: logging.Logger = logging.getLogger(__name__)
_LEASE_SECONDS: int = 120
_HEARTBEAT_SECONDS: int = 30
_CLEANUP_INTERVAL_SECONDS: int = 60


def _failure_code(error: Exception) -> str:
    if isinstance(error, (ValueError, ReporterException)):
        return 'REPORT_REQUEST_INVALID'
    if isinstance(error, (YFinanceError, ModelException, LLMException)):
        return 'REPORT_PROVIDER_FAILED'
    return 'REPORT_GENERATION_FAILED'


async def _heartbeat(
    report_id: str,
    worker_id: str,
    stop_event: asyncio.Event,
) -> None:
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=_HEARTBEAT_SECONDS,
            )
            return
        except TimeoutError:
            was_renewed: bool = await ReportRepository.renew_report_lease(
                report_id,
                worker_id,
                lease_seconds=_LEASE_SECONDS,
            )
            if not was_renewed:
                return


async def _process_report_job(job: ReportJob, worker_id: str) -> None:
    heartbeat_stop: asyncio.Event = asyncio.Event()
    heartbeat_task: asyncio.Task[None] = asyncio.create_task(
        _heartbeat(job.report_id, worker_id, heartbeat_stop),
    )
    is_personalized: bool = False

    try:
        account = await get_by_id(job.account_id)
        if account is None:
            was_failed: bool = await ReportRepository.fail_report_job(
                job.report_id,
                worker_id,
                'ACCOUNT_NOT_FOUND',
            )
            if not was_failed:
                logger.warning(
                    'Could not mark report %s failed because its lease was lost',
                    job.report_id,
                )
            return

        request_data = job.request
        ticker: Ticker = Ticker(ticker=job.ticker)
        generate_explanation: bool = bool(request_data['explain'])
        generate_charts: bool = bool(request_data['charts'])
        mode: str = str(request_data['mode'])
        horizon: int = int(request_data['ml_horizon'])
        cache_key: str | None = get_report_cache_key(
            account,
            ticker,
            generate_explanation=generate_explanation,
            generate_charts=generate_charts,
            mode=mode,
            horizon=horizon,
        )
        is_personalized = cache_key is None
        try:
            report = await generate_report(
                account,
                ticker,
                generate_explanation=generate_explanation,
                generate_charts=generate_charts,
                mode=mode,
                horizon=horizon,
                verbose=bool(request_data.get('verbose', False)),
            )
        except OllamaNotInstalledError:
            logger.error('Ollama it is the last provider available and is not installed, cannot generate report for %s', job.report_id)
            await ReportRepository.fail_report_job(
                job.report_id,
                worker_id,
                'SERVICE_UNAVAILABLE::OLLAMA_NOT_INSTALLED',
            )
            return

        renderer = smart_render_strategy.match(job.file_name.casefold())
        with TemporaryDirectory(prefix='finance-scraper-report-') as directory:
            artifact_path: Path = Path(directory) / job.file_name
            await asyncio.to_thread(
                renderer.render,
                report,
                str(artifact_path),
            )
            if not artifact_path.is_file():
                raise OSError('The report renderer did not create an artifact')
            artifact: bytes = await asyncio.to_thread(artifact_path.read_bytes)

        was_completed: bool = await ReportRepository.complete_report_job(
            job.report_id,
            worker_id,
            artifact,
            content_type=job.content_type,
            metadata=job.metadata,
            cache_key=cache_key,
            is_personalized=is_personalized,
        )
        if not was_completed:
            logger.warning(
                'Discarded report artifact for %s because its lease was lost',
                job.report_id,
            )
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.exception('Report job %s failed', job.report_id)
        try:
            was_failed = await ReportRepository.fail_report_job(
                job.report_id,
                worker_id,
                _failure_code(e),
                is_personalized=is_personalized,
            )
        except Exception:
            logger.exception('Could not persist failure for report %s', job.report_id)
        else:
            if not was_failed:
                logger.warning(
                    'Could not persist failure for report %s because its lease was lost',
                    job.report_id,
                )
    finally:
        heartbeat_stop.set()
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception('Report heartbeat failed for %s', job.report_id)


async def run_report_worker(stop_event: asyncio.Event) -> None:
    worker_id: str = uuid4().hex
    next_cleanup_at: int = 0
    active_tasks: set[Task[None]] = set()
    max_concurrency: int = get_report_worker_concurrency()
    logger.info('Report worker concurrency set to %s', max_concurrency)

    try:
        while not stop_event.is_set():
            active_tasks = {
                task
                for task in active_tasks
                if not task.done()
            }
            now: int = int(time.time())
            if not IS_DEV and now >= next_cleanup_at:
                try:
                    await ReportRepository.cleanup_expired_report_jobs(now=now)
                    await asyncio.to_thread(
                        shared_cache.cleanup_expired,
                        now=now,
                    )
                    await ReportRepository.cleanup_expired_tokens(now=now)
                except Exception:
                    logger.exception('API state cleanup failed')
                next_cleanup_at = now + _CLEANUP_INTERVAL_SECONDS

            if len(active_tasks) >= max_concurrency:
                await asyncio.wait(
                    active_tasks,
                    return_when=FIRST_COMPLETED,
                )
                continue

            try:
                job: ReportJob | None = (
                    await ReportRepository.claim_next_report_job(
                        worker_id,
                        now=now,
                        lease_seconds=_LEASE_SECONDS,
                    )
                )
            except Exception:
                logger.exception('Could not claim a pending report job')
                job = None

            if job is not None:
                task: Task[None] = asyncio.create_task(
                    _process_report_job(job, worker_id),
                    name=f'api-report-{job.report_id}',
                )
                active_tasks.add(task)
                continue

            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=settings.api.report_worker_poll_seconds,
                )
            except TimeoutError:
                continue
    finally:
        for task in active_tasks:
            task.cancel()
        if active_tasks:
            await asyncio.gather(*active_tasks, return_exceptions=True)
