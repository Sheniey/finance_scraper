
from fastapi import Request, status
from fastapi.responses import JSONResponse

from api.exceptions.base import APIException


class OllamaNotInstalledError(APIException):
    def __init__(self) -> None:
        self.error = 'OLLAMA_SERVICE_NOT_INSTALLED'
        self.message = 'The Ollama service is not installed or cannot be found in the system.'
        self.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        self.headers = {}

    @staticmethod
    async def handler(req: Request, exc: OllamaNotInstalledError) -> JSONResponse:
        return await APIException.handler(req, exc)
