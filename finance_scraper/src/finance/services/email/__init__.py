"""Email delivery service."""

from finance.services.email.exceptions import (
    EmailConfigurationError,
    EmailException,
    EmailError,
    InvalidConfigurationError,
)
from finance.services.email.models import EmailAttachment
from finance.services.email.service import (
    EmailService,
    SMTPSettings,
    build_report_notice,
    get_smtp_settings,
    send_email,
    send_report_bundle,
)


# ================================================== #
# PUBLIC EMAIL API                                   #
# ================================================== #

__all__: list[str] = [
    'EmailConfigurationError',
    'EmailAttachment',
    'EmailError',
    'EmailException',
    'EmailService',
    'InvalidConfigurationError',
    'SMTPSettings',
    'build_report_notice',
    'get_smtp_settings',
    'send_email',
    'send_report_bundle',
]
