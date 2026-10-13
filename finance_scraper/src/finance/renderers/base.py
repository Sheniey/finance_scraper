
from typing import Any, Protocol
from pathlib import Path

from finance.services.reporter import Report


# ================================================== #
# RENDERER CONTRACT                                  #
# ================================================== #

type RenderResult = None


class ReportRenderer(Protocol):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        ...

    def normalize_output(self, report: Report, output: str | None = None) -> Path:
        ...

    def render(self, report: Report, output: str | None = None) -> RenderResult:
        ...
