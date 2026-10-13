
from fastapi import Request, status
from fastapi.responses import JSONResponse

from api.exceptions.base import APIException


class AccountNotFoundError(APIException):
    def __init__(self) -> None:
        self.error = 'ACCOUNT_NOT_FOUND'
        self.message = 'The requested account could not be found'
        self.status_code = status.HTTP_404_NOT_FOUND
        self.headers = {}
        super().__init__(self.message)

    @staticmethod
    async def handler(req: Request, exc: AccountNotFoundError) -> JSONResponse:
        return await APIException.handler(req, exc)

class AccountAlreadyExistsError(APIException):
    def __init__(self) -> None:
        self.error = 'ACCOUNT_ALREADY_EXISTS'
        self.message = 'There is already an account with this email'
        self.status_code = status.HTTP_409_CONFLICT
        self.headers = {}
        super().__init__(self.message)

    @staticmethod
    async def handler(req: Request, exc: AccountAlreadyExistsError) -> JSONResponse:
        return await APIException.handler(req, exc)

class IncorrectCurrentPasswordError(APIException):
    def __init__(self) -> None:
        self.error = 'INCORRECT_CURRENT_PASSWORD'
        self.message = 'The current password is incorrect'
        self.status_code = status.HTTP_400_BAD_REQUEST
        self.headers = {}
        super().__init__(self.message)

    @staticmethod
    async def handler(req: Request, exc: IncorrectCurrentPasswordError) -> JSONResponse:
        return await APIException.handler(req, exc)
