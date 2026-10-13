
import asyncio
from uuid import UUID
from fastapi import APIRouter, Depends, status

from finance.services.account import Account
from finance.services.account.exceptions import (
    AccountAlreadyExistsError as FinanceAccountAlreadyExistsError,
    AccountNotFoundError as FinanceAccountNotFoundError,
)

from api.exceptions.account import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    IncorrectCurrentPasswordError,
)
from api.repositories import account as AccountRepository
from api.repositories import google as GoogleRepository
from api.repositories import report as ReportRepository
from api.repositories import schedules as ScheduleRepository
from api.schemas.account import (
    AccountCollectionResponse,
    AccountCreate,
    AccountDeleteResponse,
    AccountPasswordChangedResponse,
    AccountResponse,
    AccountUpdate,
    ChangePasswordRequest,
)
from api.schemas.query import CollectionQuery, get_collection_query
from api.services.auth_sessions import invalidate_tokens
from api.services.collections import collection_response
from api.services.credential_store import delete_google_refresh_token
from api.services.security import require_permission


router: APIRouter = APIRouter(prefix='/accounts', tags=['accounts'])
_ACCOUNT_FIELDS: set[str] = {
    'id',
    'name',
    'email',
    'role',
    'language',
    'custom_report',
    'watchlist',
}


def _account_id(account: Account) -> UUID:
    return account.account_id or account.id


async def _delete_account_and_sessions(account: Account) -> None:
    account_id: UUID = _account_id(account)
    account_id_text: str = str(account_id)
    google_connection = await GoogleRepository.get_google_connection(
        account_id_text,
    )
    if google_connection is not None:
        await asyncio.to_thread(
            delete_google_refresh_token,
            account_id_text,
        )
    await ScheduleRepository.delete_account_schedules(account_id_text)
    await GoogleRepository.delete_google_connection(account_id_text)
    await invalidate_tokens(account_id=account_id_text)
    await ReportRepository.delete_account_report_jobs(account_id_text)
    deleted_account: Account | None = await AccountRepository.delete_account(
        account_id,
    )
    if deleted_account is None:
        raise AccountNotFoundError()


@router.get(
    '',
    response_model=AccountCollectionResponse,
    status_code=status.HTTP_200_OK,
    summary='List accounts',
)
async def get_accounts(
    query: CollectionQuery = Depends(get_collection_query),
    admin: Account = Depends(require_permission('account:read')),
) -> AccountCollectionResponse:
    accounts: list[Account] = await AccountRepository.list_accounts()
    items: list[AccountResponse] = [
        AccountResponse.from_account(account)
        for account in accounts
    ]
    return collection_response(
        items,
        query,
        allowed_fields=_ACCOUNT_FIELDS,
        allowed_sort_fields={'id', 'name', 'email', 'role'},
        allowed_filter_fields={'name', 'email', 'role'},
        default_sort=('name',),
    )


@router.post(
    '',
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Create an account',
)
async def create_account(
    payload: AccountCreate,
    admin: Account = Depends(require_permission('account:create')),
) -> AccountResponse:
    try:
        account: Account = await AccountRepository.create_account(payload)
    except FinanceAccountAlreadyExistsError as e:
        raise AccountAlreadyExistsError() from e
    return AccountResponse.from_account(account)


@router.get(
    '/me',
    response_model=AccountResponse,
    status_code=status.HTTP_200_OK,
    summary='Get the authenticated account',
)
async def get_my_account(
    account: Account = Depends(require_permission('account-me:read')),
) -> AccountResponse:
    return AccountResponse.from_account(account)


@router.put(
    '/me',
    response_model=AccountResponse,
    status_code=status.HTTP_200_OK,
    summary='Update the authenticated account profile and watchlist',
)
async def update_my_account(
    payload: AccountUpdate,
    account: Account = Depends(require_permission('account-me:update')),
) -> AccountResponse:
    try:
        updated_account: Account = await AccountRepository.update_account(
            account,
            payload,
        )
    except FinanceAccountAlreadyExistsError as e:
        raise AccountAlreadyExistsError() from e
    except FinanceAccountNotFoundError as e:
        raise AccountNotFoundError() from e
    return AccountResponse.from_account(updated_account)


@router.delete(
    '/me',
    response_model=AccountDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary='Delete the authenticated account and revoke all sessions',
)
async def delete_my_account(
    account: Account = Depends(require_permission('account-me:delete')),
) -> AccountDeleteResponse:
    await _delete_account_and_sessions(account)
    return AccountDeleteResponse()


@router.post(
    '/me/change-password',
    response_model=AccountPasswordChangedResponse,
    status_code=status.HTTP_200_OK,
    summary='Change the authenticated account password',
)
async def change_my_password(
    payload: ChangePasswordRequest,
    account: Account = Depends(require_permission('account-me:change-password')),
) -> AccountPasswordChangedResponse:
    was_changed: bool = await AccountRepository.change_password(
        _account_id(account),
        payload.current_password.get_secret_value(),
        payload.new_password.get_secret_value(),
    )
    if not was_changed:
        raise IncorrectCurrentPasswordError()
    await invalidate_tokens(account_id=str(_account_id(account)))
    return AccountPasswordChangedResponse()


@router.get(
    '/{uuid}',
    response_model=AccountResponse,
    status_code=status.HTTP_200_OK,
    summary='Get an account by UUID',
)
async def get_account(
    uuid: UUID,
    admin: Account = Depends(require_permission('account:read')),
) -> AccountResponse:
    account: Account | None = await AccountRepository.get_account(uuid)
    if account is None:
        raise AccountNotFoundError()
    return AccountResponse.from_account(account)


@router.put(
    '/{uuid}',
    response_model=AccountResponse,
    status_code=status.HTTP_200_OK,
    summary='Update an account by UUID',
)
async def update_account(
    uuid: UUID,
    payload: AccountUpdate,
    admin: Account = Depends(require_permission('account:update')),
) -> AccountResponse:
    account: Account | None = await AccountRepository.get_account(uuid)
    if account is None:
        raise AccountNotFoundError()
    try:
        updated_account: Account = await AccountRepository.update_account(
            account,
            payload,
        )
    except FinanceAccountNotFoundError as e:
        raise AccountNotFoundError() from e
    except FinanceAccountAlreadyExistsError as e:
        raise AccountAlreadyExistsError() from e
    return AccountResponse.from_account(updated_account)


@router.delete(
    '/{uuid}',
    response_model=AccountDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary='Delete an account by UUID and revoke its sessions',
)
async def delete_account(
    uuid: UUID,
    admin: Account = Depends(require_permission('account:delete')),
) -> AccountDeleteResponse:
    account: Account | None = await AccountRepository.get_account(uuid)
    if account is None:
        raise AccountNotFoundError()
    await _delete_account_and_sessions(account)
    return AccountDeleteResponse()
