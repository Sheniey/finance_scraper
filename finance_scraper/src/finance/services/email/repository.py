"""Public entry points for user-authorized Gmail report delivery."""

from finance.services.email.service import (
    EmailService,
    build_report_notice,
    send_email,
    send_report_bundle,
)
from finance.services.email.models import EmailAttachment
