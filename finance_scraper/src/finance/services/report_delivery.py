"""Shared PDF rendering helpers for CLI and watchlist delivery."""

from pathlib import Path
from tempfile import TemporaryDirectory

from finance.services.email.models import EmailAttachment
from finance.services.reporter.models import Report


# ================================================== #
# PDF ATTACHMENTS                                    #
# ================================================== #

def render_pdf_attachment(
    report: Report,
    *,
    filename: str | None = None,
) -> EmailAttachment:
    """Render a report into an in-memory PDF attachment."""

    from finance.renderers.pdf.renderer import PDFRenderer

    attachment_name: str = filename or (
        f'report_{report.ticker.symbol.lower()}.pdf'
    )
    with TemporaryDirectory(prefix='finance-scraper-report-') as directory:
        output_path: Path = Path(directory) / attachment_name
        PDFRenderer().render(report, str(output_path))
        return EmailAttachment.from_path(
            output_path,
            filename=attachment_name,
        )


__all__: list[str] = ['render_pdf_attachment']
