from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReportSchedule:
    schedule_id: str
    account_id: str
    tickers: tuple[str, ...]
    report_format: str
    run_at: str
    timezone: str
    explain: bool
    mode: str
    charts: bool
    ml_horizon: int
    enabled: bool
    last_run_date: str | None
    last_run_status: str | None
    last_error: str | None
    created_at: int
    updated_at: int


@dataclass(frozen=True, slots=True)
class ScheduleRunResult:
    schedule_id: str
    scheduled_date: str
    status: str
    report_ids: tuple[str, ...]
