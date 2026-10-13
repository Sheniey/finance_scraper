
from fastapi import Request, status
from fastapi.responses import JSONResponse

from api.exceptions.base import APIException


class IncorrectCredentialsError(APIException):
    def __init__(self) -> None:
        self.error = 'INCORRECT_CREDENTIALS'
        self.message = 'Incorrect email or password'
        self.status_code = status.HTTP_401_UNAUTHORIZED
        self.headers = {'WWW-Authenticate': 'Bearer'}
        super().__init__(self.message)

    @staticmethod
    async def handler(req: Request, exc: IncorrectCredentialsError) -> JSONResponse:
        return await APIException.handler(req, exc)

class InvalidExpiredTokenError(APIException):
    def __init__(self) -> None:
        self.error = 'INVALID_EXPIRED_TOKEN'
        self.message = 'The provided token is invalid or has expired'
        self.status_code = status.HTTP_401_UNAUTHORIZED
        self.headers = {'WWW-Authenticate': 'Bearer'}
        super().__init__(self.message)

    @staticmethod
    async def handler(req: Request, exc: InvalidExpiredTokenError) -> JSONResponse:
        return await APIException.handler(req, exc)
