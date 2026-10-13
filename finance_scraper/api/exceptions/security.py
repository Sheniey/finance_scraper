
from fastapi import Request, status
from fastapi.responses import JSONResponse

from api.core.roles import Role
from api.exceptions.base import APIException


class DesktopControlDisabledError(APIException):
    def __init__(self) -> None:
        self.error = 'DESKTOP_CONTROL_NOT_CONFIGURED'
        self.message = 'Desktop control is not configured for this API process'
        self.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        self.headers = {}
        super().__init__(self.message)


class DesktopControlUnauthorizedError(APIException):
    def __init__(self) -> None:
        self.error = 'DESKTOP_CONTROL_UNAUTHORIZED'
        self.message = 'A valid desktop control token is required'
        self.status_code = status.HTTP_403_FORBIDDEN
        self.headers = {}
        super().__init__(self.message)


class DesktopServerControlUnavailableError(APIException):
    def __init__(self) -> None:
        self.error = 'DESKTOP_SERVER_CONTROL_UNAVAILABLE'
        self.message = 'The API server does not expose desktop lifecycle control'
        self.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        self.headers = {}
        super().__init__(self.message)


class UnauthorizedError(APIException):
    def __init__(self, role: Role | None = None) -> None:
        self.error = 'PERMISSION_DENIED'
        role_name: str = role.name if role is not None else 'unknown'
        self.message = f'Role {role_name!r} is not permitted to perform this action'
        self.status_code = status.HTTP_403_FORBIDDEN
        self.headers = {}
        super().__init__(self.message)

    @staticmethod
    async def handler(req: Request, exc: UnauthorizedError) -> JSONResponse:
        return await APIException.handler(req, exc)
