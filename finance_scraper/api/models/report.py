from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ReportStatus(StrEnum):
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'


class ReportFormat(StrEnum):
    PDF = 'pdf'
    JSON = 'json'
    YAML = 'yaml'
    TXT = 'txt'
    XLSX = 'xlsx'

    @property
    def content_type(self) -> str:
        match self:
            case ReportFormat.PDF:
                return 'application/pdf'
            case ReportFormat.JSON:
                return 'application/json'
            case ReportFormat.YAML:
                return 'application/yaml'
            case ReportFormat.TXT:
                return 'text/plain'
            case ReportFormat.XLSX:
                return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


@dataclass(frozen=True, slots=True)
class ReportJob:
    report_id: str
    account_id: str
    ticker: str
    request: dict[str, Any]
    status: ReportStatus
    file_name: str
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
    worker_id: str | None = None
    lease_until: int | None = None
