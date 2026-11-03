from pydantic import BaseModel, EmailStr, Field, SecretStr

from api.schemas.account import AccountCreate
from api.schemas.base import OKResponse


class RegistrationRequest(AccountCreate):
    pass


class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)


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
