
from fastapi import Request
from fastapi.responses import JSONResponse

from api.schemas.base import ErrorResponse


class APIException(Exception):
    error: str
    message: str
    status_code: int
    headers: dict[str, str]

    def __init__(self, message: str) -> None:
        self.headers = self.headers if hasattr(self, 'headers') else {}
        super().__init__(message)

    @staticmethod
    async def handler(req: Request, exc: APIException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content=ErrorResponse(
                error=exc.error,
                message=exc.message[:256],
                status_code=exc.status_code,
            ).model_dump(),
        )
