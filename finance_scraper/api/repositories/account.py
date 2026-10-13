
from uuid import UUID

from finance.config import DEFAULT_LANGUAGE
from finance.services.account import (
    Account,
    change_password as change_account_password,
    create_account as persist_account,
    delete_account as remove_account,
    get_by_id,
    get_everyone,
    get_account_with_password_by_email,
    update_account as persist_account_update,
)
from finance.types.language import Language

from api.schemas.account import AccountCreate, AccountUpdate


async def list_accounts() -> list[Account]:
    return await get_everyone()

async def get_account(account_id: UUID) -> Account | None:
    return await get_by_id(account_id)


async def get_account_by_email(email: str) -> Account | None:
    account, _ = await get_account_with_password_by_email(email)
    return account


async def create_account(payload: AccountCreate) -> Account:
    language: Language = payload.language or Language(**DEFAULT_LANGUAGE)
    account: Account = Account(
        name=payload.name,
        email=payload.email,
        role='user',
        language=language,
        custom_report=payload.custom_report,
        watchlist=payload.watchlist,
        portfolio=payload.portfolio,
    )
    return await persist_account(
        account,
        payload.password.get_secret_value(),
    )

async def update_account(
    account: Account,
    payload: AccountUpdate,
) -> Account:
    updated_account: Account = account.model_copy(
        update={
            'name': payload.name,
            'email': payload.email,
            'language': payload.language or account.language,
            'custom_report': (
                payload.custom_report
                if payload.custom_report is not None
                else account.custom_report
            ),
            'watchlist': (
                payload.watchlist
                if payload.watchlist is not None
                else account.watchlist
            ),
            'portfolio': (
                payload.portfolio
                if payload.portfolio is not None
                else account.portfolio
            ),
        },
    )
    return await persist_account_update(updated_account)

async def delete_account(account_id: UUID) -> Account | None:
    return await remove_account(account_id)

async def change_password(
    account_id: UUID,
    current_password: str,
    new_password: str,
) -> bool:
    return await change_account_password(
        account_id,
        current_password,
        new_password,
    )
