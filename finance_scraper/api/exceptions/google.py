from fastapi import status

from api.exceptions.base import APIException


class GoogleOAuthNotConfiguredError(APIException):
    def __init__(self) -> None:
        self.error = 'GOOGLE_OAUTH_NOT_CONFIGURED'
        self.message = 'A Google OAuth desktop client ID must be configured'
        self.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        self.headers = {}
        super().__init__(self.message)


class GoogleOAuthFlowError(APIException):
    def __init__(
        self,
        message: str = 'The Google authorization flow is invalid or expired',
    ) -> None:
        self.error = 'GOOGLE_OAUTH_FLOW_INVALID'
        self.message = message
        self.status_code = status.HTTP_400_BAD_REQUEST
        self.headers = {}
        super().__init__(self.message)


class GoogleOAuthProviderError(APIException):
    def __init__(
        self,
        message: str = 'Google could not complete the authorization request',
    ) -> None:
        self.error = 'GOOGLE_OAUTH_PROVIDER_FAILED'
        self.message = message
        self.status_code = status.HTTP_502_BAD_GATEWAY
        self.headers = {}
        super().__init__(self.message)


class GoogleAccountNotConnectedError(APIException):
    def __init__(self) -> None:
        self.error = 'GOOGLE_ACCOUNT_NOT_CONNECTED'
        self.message = 'Connect a Google account before sending reports'
        self.status_code = status.HTTP_409_CONFLICT
        self.headers = {}
        super().__init__(self.message)


class CredentialStoreUnavailableError(APIException):
    def __init__(self) -> None:
        self.error = 'SECURE_CREDENTIAL_STORE_UNAVAILABLE'
        self.message = 'Windows Credential Manager is not available'
        self.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        self.headers = {}
        super().__init__(self.message)
