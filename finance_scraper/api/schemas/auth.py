from typing import Literal

from pydantic import BaseModel, EmailStr, Field, SecretStr

from api.schemas.account import AccountCreate
from api.schemas.base import OKResponse


class RegistrationRequest(AccountCreate):
    pass


class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)


class GoogleLoginFlowRequest(BaseModel):
    flow_id: str = Field(min_length=32, max_length=128)


class GoogleLoginFlowResponse(OKResponse):
    status: Literal['pending', 'completed', 'failed']
    email: EmailStr | None = None
    name: str | None = None
    error: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: SecretStr


class TokenPairResponse(OKResponse):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    expires_in: int
    refresh_expires_in: int


class LogoutResponse(OKResponse):
    message: str = 'Successfully logged out'
