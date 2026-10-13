
from designkit.behavioral.matcher import Matcher, Searcher

from finance.renderers.factory import RendererFactory
from finance.renderers.exceptions import RendererNotFoundError


# ================================================== #
# RENDERER MATCHING                                  #
# ================================================== #

renderer: Matcher = Matcher[RendererFactory]()


@renderer.case(
    r'(?P<name>.*)'
    r'(?P<format>csv|tsv|excel|xlsx)'
)
def dataframe_handler(searcher: Searcher) -> RendererFactory:
    format: str = searcher.as_string('format')
    return RendererFactory.create({
        'csv': 'csv',
        'tsv': 'tsv',
        'excel': 'xlsx',
        'xlsx': 'xlsx'
    }.get(format, 'csv'))


@renderer.case(
    r'(?P<name>.*)'
    r'(?P<format>json|yaml|toml|xml)'
    r'(?:(?:\:|\-)?(?P<indent>[0-9]+))?'
)
def nosql_handler(searcher: Searcher) -> RendererFactory:
    format: str = searcher.as_string('format')
    indent_value: str | None = searcher.group('indent')
    indent: int = int(indent_value) if indent_value else 4
    return RendererFactory.create(format, indent=indent)


@renderer.case(
    r'(?P<name>.*)'
    r'(?P<format>pdf|docx|word)'
    r'(?:(?:\:|\-)?(?P<pagesize>letter|half_letter|a0|a1|a2|a3|a4|a5|a6|b0|b1|b2|b3|b4|b5|b6|c0|c1|c2|c3|c4|c5|c6|legal|tabloid|ledger))?'
)
def document_handler(searcher: Searcher) -> RendererFactory:
    format: str = searcher.as_string('format')
    pagesize_value: str | None = searcher.group('pagesize')
    pagesize: str = pagesize_value or 'letter'
    if format != 'pdf':
        raise ValueError(f'Word document format is not supported yet')
    
    return RendererFactory.create({
        'pdf': 'pdf',
        'docx': 'docx',
        'word': 'docx'
    }.get(format, 'pdf'), pagesize=pagesize)


@renderer.case(
    r'(?P<name>.*)'
    r'(?P<format>html|htm|page|site)'
    r'(?:(?:\:|\-)?(?P<kind>page|site))?'
)
def html_handler(searcher: Searcher) -> RendererFactory:
    kind_value: str | None = searcher.group('kind')
    kind: str = kind_value or 'page'
    if kind == 'site':
        return RendererFactory.create('html-site')
    return RendererFactory.create('html-page')


@renderer.case(
    r'(?P<name>.*)'
    r'(?P<format>console|terminal|stdout|stderr)'
)
def console_handler(searcher: Searcher) -> RendererFactory:
    return RendererFactory.create('console')


@renderer.case(
    r'(?P<name>.*)'
    r'(?P<format>text|txt)'
)
def text_handler(searcher: Searcher) -> RendererFactory:
    return RendererFactory.create('txt')


@renderer.case(r'(?P<path>.*)')
def fallback_handler(searcher: Searcher) -> RendererFactory:
    raise RendererNotFoundError(searcher.as_string('path'))
