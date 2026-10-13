"""Compatibility exports for email delivery functions."""

from finance.services.email.service import (
    EmailService,
    SMTPSettings,
    build_report_notice,
    get_smtp_settings,
    send_email,
    send_report_bundle,
)
from finance.services.email.models import EmailAttachment


# ================================================== #
# PUBLIC EMAIL API                                   #
# ================================================== #

__all__: list[str] = [
    'EmailService',
    'EmailAttachment',
    'SMTPSettings',
    'build_report_notice',
    'get_smtp_settings',
    'send_email',
    'send_report_bundle',
]
