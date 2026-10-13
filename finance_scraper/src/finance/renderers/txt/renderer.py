# ================================================== #
# MODULE: renderer
# ================================================== #


import datetime
from pathlib import Path
from typing import Any

from finance.services.reporter import Report
from finance.services.llm import ExplanationConfig
from finance.services.llm.repository import build_user
from finance.renderers.utils import fallback_to_console, normalize_output


class TXTRenderer:
    def __init__(self, *args: Any, **kwargs: dict[str, Any]) -> None:
        self.args: tuple[Any, ...] = args
        self.kwargs: dict[str, Any] = kwargs

    def normalize_output(self, report: Report, output: str | None = None) -> Path:
        destination: str = normalize_output(output, report, 'txt')
        root: Path = Path(destination or f'report_{report.ticker.symbol.upper()}--{datetime.now().strftime("%Y-%m-%d")}.txt')
        root.mkdir(parents=True, exist_ok=True)
        return root

    def render(self, report: Report, output: str | None = None) -> None:
        destination: str | None = normalize_output(output, report, 'txt')
        payload: str = build_user(ExplanationConfig(
            action=report.prediction_result.top_action,
            possible_actions=[act.action for act in report.prediction_result.action_probabilities],
            account=report.account,
            ticker=report.ticker,
            news_compilation=report.news_compilation,
            analysis=report.analysis,
            mode=report.mode,
            prediction_result=report.prediction_result,
            charts=report.charts,
            explanation=report.explanation,
        ))

        def _load2file(dest: Path) -> None:
            with open(dest, mode='w', encoding='utf-8') as f:
                f.write(payload)

        fallback_to_console(destination, payload, _load2file)
