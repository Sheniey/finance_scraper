# ================================================== #
# MODULE: observer
# ================================================== #


from typing import Any, Protocol
from dataclasses import dataclass, field

from finance.types.report import Report


class ReportObserver(Protocol):
    def update(self, report: Report) -> None: ...


class ReportStage(Protocol):
    async def run(self, context: dict[str, Any]) -> None: ...


@dataclass
class ReportPipeline:
    stages: list[ReportStage] = field(default_factory=list)

    async def run(self, context: dict[str, Any]) -> None:
        for stage in self.stages:
            await stage.run(context)
