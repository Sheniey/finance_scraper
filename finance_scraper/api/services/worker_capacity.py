import psutil

from api.core.config import settings


def get_report_worker_concurrency() -> int:
    logical_cpus: int = psutil.cpu_count(logical=True) or 1
    available_memory_bytes: int = psutil.virtual_memory().available
    cpu_slots: int = max(1, logical_cpus // 2)
    memory_slots: int = max(1, available_memory_bytes // (4 * 1024**3))
    return min(
        cpu_slots,
        memory_slots,
        settings.api.report_worker_max_concurrency,
    )
