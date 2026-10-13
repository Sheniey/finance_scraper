from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class StoredReportJob:
    report_id: str
    account_id: str
    resource: str
    request: dict[str, Any]
    status: str
    filename: str
    report_format: str
    content_type: str
    metadata: dict[str, Any]
    artifact: bytes | None
    cache_key: str | None
    is_personalized: bool
    source: str
    error_code: str | None
    created_at: int
    updated_at: int
    started_at: int | None
    completed_at: int | None
    expires_at: int | None
    worker_id: str | None
    lease_until: int | None
