from typing import Literal

from pydantic import EmailStr, Field

from api.schemas.base import OKResponse


class GoogleAuthorizationResponse(OKResponse):
    flow_id: str
    authorization_url: str


class GoogleAccountStatusResponse(OKResponse):
    connected: bool
    email: EmailStr | None = None
    scopes: list[str] = Field(default_factory=list)


class GoogleDisconnectResponse(OKResponse):
    disabled_schedule_ids: list[str] = Field(default_factory=list)


class GoogleFlowStatusResponse(OKResponse):
    status: Literal['pending', 'completed', 'failed']
    email: EmailStr | None = None
    error: str | None = None
