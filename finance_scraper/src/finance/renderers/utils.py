# ================================================== #
# MODULE: utils
# ================================================== #


import re
from typing import Any, Callable
from datetime import datetime
from pathlib import Path
from httpx import AsyncClient

from finance.config import console
from finance.services.reporter import Report


def normalize_output(output: str | None, report: Report, format: str) -> str | None:
    """Return a formatted path, or `None` when output belongs on the console."""
    normalized_format: str = format.strip().lower().lstrip('.')
    if not normalized_format:
        raise ValueError('Renderer format cannot be empty.')

    if output is None or not output.strip():
        return None

    destination: str = output.strip()
    console_tokens: set[str] = { normalized_format, 'auto' }
    if normalized_format == 'html-site':
        console_tokens.add('site')
    if normalized_format == 'txt':
        console_tokens.add('text')

    destination_lower: str = destination.lower()
    is_renderer_token: bool = re.fullmatch(
        rf'{re.escape(normalized_format)}(?:[:-][0-9]+)?',
        destination_lower,
    ) is not None
    if destination_lower in console_tokens or is_renderer_token:
        return None

    destination: str = destination.format(
        ticker=report.ticker.symbol.upper(),
        date=datetime.now().strftime('%Y-%m-%d'),
        account=report.account.name.lower().replace(' ', '_'),
        email=report.account.email.lower().replace('@', '_').replace('.', '_')
    )
    return str(Path(destination))

def fallback_to_console(destination: str | None, payload: Any, callback: Callable[[Path], None]) -> None:
    if destination:
        try:
            dest: Path = Path(destination)
            dest.parent.mkdir(parents=True, exist_ok=True)
            callback(dest)
        except OSError as e:
            console.print(f'[red]Error writing to output file "{destination}": {e}[/red]')
            console.print(payload)
    else:
        console.print(payload)

async def get_logo(report: Report) -> str | None:
    """
    Return a blob of the logo of the report's ticker, or `None` if no logo is available.
    This is fetched from `cdn.gbm.com/`
    """
    url = f'https://cdn.gbm.com/instruments/logo/{report.ticker.symbol}'
    async with AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            return response.content
    return None
