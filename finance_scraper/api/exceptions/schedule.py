from fastapi import status

from api.exceptions.base import APIException


class ScheduleNotFoundError(APIException):
    def __init__(self) -> None:
        self.error = 'SCHEDULE_NOT_FOUND'
        self.message = 'The scheduled report was not found'
        self.status_code = status.HTTP_404_NOT_FOUND
        self.headers = {}
        super().__init__(self.message)


class ScheduleLimitExceededError(APIException):
    def __init__(self) -> None:
        self.error = 'SCHEDULE_LIMIT_EXCEEDED'
        self.message = 'An account can create up to 20 report schedules'
        self.status_code = status.HTTP_429_TOO_MANY_REQUESTS
        self.headers = {}
        super().__init__(self.message)
