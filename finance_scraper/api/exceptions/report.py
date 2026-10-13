 
from fastapi import Request, status
from fastapi.responses import JSONResponse

from api.exceptions.base import APIException


class ReportNotFoundError(APIException):
    def __init__(self) -> None:
        self.error = 'REPORT_NOT_FOUND'
        self.message = 'The requested report could not be found'
        self.status_code = status.HTTP_404_NOT_FOUND
        self.headers = {}
        super().__init__(self.message)

    @staticmethod
    async def handler(req: Request, exc: ReportNotFoundError) -> JSONResponse:
        return await APIException.handler(req, exc)

class ReportNotReadyError(APIException):
    def __init__(self) -> None:
        self.error = 'REPORT_NOT_READY'
        self.message = 'The report is not yet available for download'
        self.status_code = status.HTTP_409_CONFLICT
        self.headers = {}
        super().__init__(self.message)

    @staticmethod
    async def handler(req: Request, exc: ReportNotReadyError) -> JSONResponse:
        return await APIException.handler(req, exc)

class ReportArtifactNotFoundError(APIException):
    def __init__(self) -> None:
        self.error = 'REPORT_ARTIFACT_NOT_FOUND'
        self.message = 'The report artifact is no longer available'
        self.status_code = status.HTTP_410_GONE
        self.headers = {}
        super().__init__(self.message)

    @staticmethod
    async def handler(req: Request, exc: ReportArtifactNotFoundError) -> JSONResponse:
        return await APIException.handler(req, exc)

class InvalidCollectionQueryError(APIException):
    def __init__(self, message: str) -> None:
        self.error = 'INVALID_COLLECTION_QUERY'
        self.message = message
        self.status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        self.headers = {}
        super().__init__(self.message)

    @staticmethod
    async def handler(req: Request, exc: InvalidCollectionQueryError) -> JSONResponse:
        return await APIException.handler(req, exc)
