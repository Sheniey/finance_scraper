import pytest
from pydantic import ValidationError

from api.core.config import APISettings


def test_report_retention_defaults_to_fifteen_days() -> None:
    assert APISettings().report_retention_seconds == 15 * 24 * 60 * 60


@pytest.mark.parametrize(
    'retention_seconds',
    [599, 30 * 24 * 60 * 60 + 1],
)
def test_report_retention_rejects_values_outside_configured_range(
    retention_seconds: int,
) -> None:
    with pytest.raises(ValidationError):
        APISettings(report_retention_seconds=retention_seconds)


def test_report_retention_accepts_ten_minutes_and_thirty_days() -> None:
    assert APISettings(report_retention_seconds=600).report_retention_seconds == 600
    assert (
        APISettings(
            report_retention_seconds=30 * 24 * 60 * 60,
        ).report_retention_seconds
        == 30 * 24 * 60 * 60
    )
