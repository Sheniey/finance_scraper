
from finance.types.report_mode import ReportMode


# ================================================== #
# GLOBAL EXCEPTIONS                                  #
# ================================================== #

class ReporterException(Exception):
    """Global exception for the reporter service."""
    pass


# ================================================== #
# CUSTOM REPORT EXCEPTIONS                          #
# ================================================== #

class InvalidReportModeError(ReporterException, ValueError):
    """Raised when a report mode is invalid."""

    def __init__(self, mode: ReportMode | str) -> None:
        self.mode: ReportMode | str = mode
        super().__init__(f'Invalid report mode: {mode!r}')

class InvalidCustomReportError(ReporterException, ValueError):
    """Raised when a custom report configuration is invalid."""

    def __init__(
        self,
        message: str,
        unknown_metrics: tuple[str, ...] = (),
    ) -> None:
        self.message: str = message
        self.unknown_metrics: tuple[str, ...] = unknown_metrics
        super().__init__(message)

class InvalidReportHorizonError(ReporterException, ValueError):
    """Raised when a report horizon is not positive."""

    def __init__(self, horizon: int) -> None:
        self.horizon: int = horizon
        super().__init__('horizon must be positive.')
