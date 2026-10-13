
from typing import Any, Literal
from designkit.behavioral.typing import Assertion

from finance.renderers.exceptions import RendererNotFoundError
from finance.services.reporter.models import Report
from finance.renderers.base import ReportRenderer

# ================================================== #
# RENDERER FACTORY                                   #
# ================================================== #

class RendererFactory:
    def __init__(self, renderer: ReportRenderer) -> None:
        self.__renderer: ReportRenderer = renderer

    @classmethod
    def create(
        cls,
        id: Literal[
            'console',
            'pdf',
            'json',
            'yaml',
            'txt',
            'xlsx',
            'html',
            'html-page',
            'html-site',
        ],
        *args: Any,
        **kwargs: Any,
    ) -> ReportRenderer:
        Assertion(id).must_be(str)

        match id.strip().lower():
            case 'console':
                from finance.renderers.console import ConsoleRenderer

                return ConsoleRenderer(*args, **kwargs)
            case 'pdf':
                from finance.renderers.pdf.renderer import PDFRenderer

                return PDFRenderer(*args, **kwargs)
            case 'json':
                from finance.renderers.json.renderer import JSONRenderer

                return JSONRenderer(*args, **kwargs)
            case 'yaml':
                from finance.renderers.yaml.renderer import YAMLRenderer

                return YAMLRenderer(*args, **kwargs)
            case 'txt':
                from finance.renderers.txt.renderer import TXTRenderer

                return TXTRenderer(*args, **kwargs)
            case 'xlsx':
                from finance.renderers.xlsx.renderer import XLSXRenderer

                return XLSXRenderer(*args, **kwargs)
            case 'html' | 'html-page':
                from finance.renderers.html import HTMLPageRenderer

                return HTMLPageRenderer(*args, **kwargs)
            case 'html-site':
                from finance.renderers.html import HTMLSiteRenderer

                return HTMLSiteRenderer(*args, **kwargs)
            case _:
                raise RendererNotFoundError(id)

    def render(self, report: Report, output: str | None) -> None:
        self.__renderer.render(report, output)
