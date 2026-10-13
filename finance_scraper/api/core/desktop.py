import hmac
import os
from typing import Annotated

from fastapi import Header

from api.exceptions.security import (
    DesktopControlDisabledError,
    DesktopControlUnauthorizedError,
)


def require_desktop_control_token(
    token: Annotated[
        str | None,
        Header(alias='X-Finance-Desktop-Token'),
    ] = None,
) -> None:
    expected_token: str | None = os.getenv('FINANCE_DESKTOP_CONTROL_TOKEN')
    if not expected_token:
        raise DesktopControlDisabledError()
    if token is None or not hmac.compare_digest(token, expected_token):
        raise DesktopControlUnauthorizedError()
