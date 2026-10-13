from datetime import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator

from datatypes.ticker import Ticker
from finance.types.report_mode import ReportMode

from api.models.report import ReportFormat
from api.schemas.base import OKResponse


class ScheduleCreate(BaseModel):
    tickers: list[str] = Field(min_length=1, max_length=10)
    report_format: ReportFormat = ReportFormat.PDF
    run_at: time
    timezone: str
    explain: bool = False
    mode: ReportMode = ReportMode.CUSTOM
    charts: bool = True
    ml_horizon: int = Field(default=15, ge=1, le=365)

    @field_validator('tickers')
    @classmethod
    def normalize_tickers(cls, values: list[str]) -> list[str]:
        normalized: list[str] = [
            Ticker(ticker=value.strip().upper()).ticker
            for value in values
        ]
        if len(set(normalized)) != len(normalized):
            raise ValueError('tickers must be unique')
        return normalized

    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as e:
            raise ValueError('timezone must be a valid IANA time zone') from e
        return value

    @field_validator('run_at')
    @classmethod
    def normalize_run_at(cls, value: time) -> time:
        if value.second or value.microsecond:
            raise ValueError('run_at must use minute precision')
        return value


class ScheduleUpdate(BaseModel):
    enabled: bool


class ScheduleResponse(OKResponse):
    schedule_id: str
    tickers: list[str]
    report_format: ReportFormat
    run_at: str
    timezone: str
    explain: bool
    mode: ReportMode
    charts: bool
    ml_horizon: int
    enabled: bool
    last_run_date: str | None = None
    last_run_status: str | None = None
    last_error: str | None = None


class ScheduleListResponse(OKResponse):
    schedules: list[ScheduleResponse]


class ScheduleRunResponse(OKResponse):
    schedule_id: str
    scheduled_date: str
    status: str
    report_ids: list[str]


class ScheduleRunBatchResponse(OKResponse):
    runs: list[ScheduleRunResponse]


class ScheduleTaskResponse(BaseModel):
    schedule_id: str
    run_at: str
    enabled: bool


class ScheduleTaskRegistryResponse(OKResponse):
    schedules: list[ScheduleTaskResponse]
