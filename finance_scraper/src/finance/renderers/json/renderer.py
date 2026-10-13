# ================================================== #
# MODULE: renderer
# ================================================== #


import json
from pathlib import Path
from typing import Any
from rich.syntax import Syntax

from finance.config import console
from finance.services.reporter import Report
from finance.renderers.utils import normalize_output


class JSONRenderer:
    def __init__(self, *args: Any, **kwargs: dict[str, Any]) -> None:
        self.args: tuple[Any, ...] = args
        self.kwargs: dict[str, Any] = kwargs

        self.__indent: int = self.kwargs.get('indent', 4)

    def render(self, report: Report, output: str | None = None) -> None:
        payload: str = report.model_dump_json(indent=self.__indent)
        
        destination = normalize_output(output, report, 'json')
        if destination:
            destination_path = Path(destination)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            with open(destination_path, 'w', encoding='utf-8') as f:
                f.write(payload)
        else:
            console.print(Syntax(payload, 'json', theme='monokai', line_numbers=True, indent_guides=True, word_wrap=True))
