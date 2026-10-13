from types import SimpleNamespace
import asyncio

import api.services.worker_capacity as worker_capacity
import api.services.report_worker as report_worker


def test_report_worker_concurrency_uses_cpu_memory_and_hard_cap(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        worker_capacity.psutil,
        'cpu_count',
        lambda logical=True: 8,
    )
    monkeypatch.setattr(
        worker_capacity.psutil,
        'virtual_memory',
        lambda: SimpleNamespace(available=16 * 1024**3),
    )

    assert worker_capacity.get_report_worker_concurrency() == 4


def test_report_worker_concurrency_never_exceeds_one_on_small_machine(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        worker_capacity.psutil,
        'cpu_count',
        lambda logical=True: 2,
    )
    monkeypatch.setattr(
        worker_capacity.psutil,
        'virtual_memory',
        lambda: SimpleNamespace(available=2 * 1024**3),
    )

    assert worker_capacity.get_report_worker_concurrency() == 1


def test_report_worker_processes_jobs_concurrently(
    monkeypatch,
) -> None:
    monkeypatch.setattr(report_worker, 'get_report_worker_concurrency', lambda: 2)
    monkeypatch.setattr(report_worker, 'IS_DEV', True)
    jobs = [
        SimpleNamespace(report_id='rep_one'),
        SimpleNamespace(report_id='rep_two'),
    ]
    active_jobs: int = 0
    maximum_active_jobs: int = 0
    completed_jobs: int = 0
    next_job: int = 0

    async def claim_next_report_job(*args, **kwargs):
        nonlocal next_job
        if next_job == len(jobs):
            return None
        job = jobs[next_job]
        next_job += 1
        return job

    async def process_report_job(job, worker_id: str) -> None:
        nonlocal active_jobs, maximum_active_jobs, completed_jobs
        active_jobs += 1
        maximum_active_jobs = max(maximum_active_jobs, active_jobs)
        await asyncio.sleep(0.05)
        active_jobs -= 1
        completed_jobs += 1
        if completed_jobs == len(jobs):
            stop_event.set()

    monkeypatch.setattr(
        report_worker.ReportRepository,
        'claim_next_report_job',
        claim_next_report_job,
    )
    monkeypatch.setattr(
        report_worker,
        '_process_report_job',
        process_report_job,
    )

    async def scenario() -> None:
        await report_worker.run_report_worker(stop_event)

    stop_event: asyncio.Event = asyncio.Event()
    asyncio.run(scenario())

    assert completed_jobs == 2
    assert maximum_active_jobs == 2
