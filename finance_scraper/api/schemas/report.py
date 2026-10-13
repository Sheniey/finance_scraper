
import re
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, PositiveInt, field_validator

from datatypes.ticker import Ticker

from finance.types.report_mode import ReportMode

from api.models.report import ReportFormat, ReportStatus
from api.schemas.base import CollectionResponse, OKResponse


_SAFE_FILE_NAME: re.Pattern[str] = re.compile(
    r'^[A-Za-z0-9][A-Za-z0-9._ -]{0,119}$',
)
_RESERVED_FILE_NAMES: frozenset[str] = frozenset(
    {
        'AUX',
        'CLOCK$',
        'CON',
        'NUL',
        'PRN',
    },
)


class ReportCreate(BaseModel):
    ticker: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description='The stock ticker symbol to analyze, TICKER.REGION',
    )
    filename: str = Field(
        ...,
        description='Safe output filename. Its extension selects the artifact format.',
    )
    explain: bool = Field(
        False,
        description='Whether to include an explanation made by Nexis AI in the report',
    )
    mode: ReportMode = Field(
        ReportMode.CUSTOM,
        description='The preset mode for rendering of the report',
    )
    charts: bool = Field(True, description='Whether to include charts in the report')
    ml_horizon: PositiveInt = Field(
        15,
        description='The machine learning horizon for predictions in the report',
    )

    @field_validator('ticker')
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        normalized: str = value.strip().upper()
        if not normalized:
            raise ValueError('ticker must not be blank')
        return Ticker(ticker=normalized).ticker

    @field_validator('filename')
    @classmethod
    def validate_filename(cls, value: str) -> str:
        normalized: str = value.strip()
        if (
            not normalized
            or '/' in normalized
            or '\\' in normalized
            or normalized.endswith((' ', '.'))
            or not _SAFE_FILE_NAME.fullmatch(normalized)
        ):
            raise ValueError('filename must be a safe filename without a directory')
        stem: str = normalized.split('.', maxsplit=1)[0].strip(' .').upper()
        if (
            stem in _RESERVED_FILE_NAMES
            or re.fullmatch(r'(?:COM|LPT)[1-9]', stem) is not None
        ):
            raise ValueError('filename cannot use a reserved filesystem name')
        suffix: str = Path(normalized).suffix.lower().lstrip('.')
        try:
            ReportFormat(suffix)
        except ValueError as e:
            raise ValueError(
                'filename must use .pdf, .json, .yaml, .txt or .xlsx',
            ) from e
        return normalized

    @property
    def report_format(self) -> ReportFormat:
        extension: str = Path(self.filename).suffix.lower().lstrip('.')
        return ReportFormat(extension)


class ReportStatusResponse(OKResponse):
    report_id: str
    status: ReportStatus
    ticker: str
    filename: str
    report_format: str
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    expires_at: datetime | None = None
    error_code: str | None = None
    download_url: str | None = None


class ReportCollectionResponse(CollectionResponse):
    pass


class ReportBatchResponse(OKResponse):
    report_ids: list[str]
    count: int


class ReportDeleteResponse(OKResponse):
    deleted: int
    message: str = 'Report sources deleted successfully'
