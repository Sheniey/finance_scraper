
from typing import TYPE_CHECKING, Any

from finance.types.language import Language, LangStyle
from finance.types.report_mode import ReportMode
from finance.types.report_presets import get_preset, ReportPreset

if TYPE_CHECKING:
    from finance.types.report import Report


__all__: list[str] = [
    'Language',
    'LangStyle',
    'Report',
    'ReportMode',
    'ReportPreset',
    'get_preset',
]


def __getattr__(name: str) -> Any:
    if name == 'Report':
        from finance.types.report import Report

        return Report
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
