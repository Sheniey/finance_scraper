
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator

from finance.services.account.models import (
    Account,
    Stock,
    WatchlistItem,
)
from finance.types.language import Language

from api.schemas.base import CollectionResponse, OKResponse


class AccountResponse(OKResponse):
    id: UUID
    name: str
    email: EmailStr
    role: str
    language: Language
    custom_report: list[str]
    watchlist: list[WatchlistItem | None]

    @classmethod
    def from_account(cls, account: Account) -> 'AccountResponse':
        return cls(
            id=account.account_id or account.id,
            name=account.name,
            email=account.email,
            role=account.role,
            language=account.language,
            custom_report=account.custom_report,
            watchlist=account.watchlist,
        )

class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: SecretStr = Field(min_length=8, max_length=128)
    language: Language | None = None
    custom_report: list[str] = Field(default_factory=list)
    watchlist: list[WatchlistItem | None] = Field(default_factory=list)
    portfolio: list[Stock | None] = Field(default_factory=list)

    @field_validator('name')
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized: str = value.strip()
        if not normalized:
            raise ValueError('Name must not be blank')
        return normalized

class AccountUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    language: Language | None = None
    custom_report: list[str] | None = None
    watchlist: list[WatchlistItem | None] | None = None
    portfolio: list[Stock | None] | None = None

    @field_validator('name')
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized: str = value.strip()
        if not normalized:
            raise ValueError('Name must not be blank')
        return normalized

class ChangePasswordRequest(BaseModel):
    current_password: SecretStr = Field(min_length=1, max_length=128)
    new_password: SecretStr = Field(min_length=8, max_length=128)

class AccountDeleteResponse(OKResponse):
    message: str = 'Account deleted successfully'

class AccountPasswordChangedResponse(OKResponse):
    message: str = 'Password changed successfully; all sessions have been revoked'

class AccountCollectionResponse(CollectionResponse):
    pass
