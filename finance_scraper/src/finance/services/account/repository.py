
import asyncio
from enum import StrEnum
from typing import Literal, Protocol
from uuid import UUID

from designkit.behavioral.typing import Assertion

from datatypes.ticker import Ticker

from finance.services.account.exceptions import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
)
from finance.services.account.models import Account, Action, Stock, WatchlistItem
from finance.services.account.db import (
    create_account as persist_account,
    get_account_by_id as load_account_by_id,
    get_account_with_password,
    get_account_with_password_by_email,
    get_account_with_password_by_name,
    load_accounts,
    update_account as persist_account_update,
    update_password_hash as persist_password_hash,
)
from finance_core.security import hash_password, verify_password

# ================================================== #
# TYPE ALIASES                                       #
# ================================================== #

type MaybeAccount = Account | None
type PasswordHash = str


# ================================================== #
# PROTOCOLS                                          #
# ================================================== #

class AccountRepository(Protocol):
    """
    Application-facing account persistence contract.
    """

    async def get_everyone(self) -> list[Account]:
        ...

    async def get_by_id(self, account_id: UUID | str) -> MaybeAccount:
        ...

    async def get_by_email(self, email: str, password: str) -> MaybeAccount:
        ...

    async def get_by_name(self, name: str, password: str) -> MaybeAccount:
        ...

    async def create(self, account: Account, password: str) -> Account:
        ...

    async def update(self, account: Account) -> Account:
        ...


# ================================================== #
# ACCOUNT REPOSITORY                                 #
# ================================================== #

class SQLiteAccountRepository:
    """
    Persist accounts through the normalized Turso/libSQL account store.
    """

    async def get_everyone(self) -> list[Account]:
        return await load_accounts()

    async def get_by_id(self, account_id: UUID | str) -> MaybeAccount:
        return await load_account_by_id(account_id)

    async def get_by_email(self, email: str, password: str) -> MaybeAccount:
        Assertion(email).must_be(str)
        if not Assertion(password).should_be(str) or not password.strip():
            raise ValueError('A password is required to load an account')

        account, password_hash = await get_account_with_password_by_email(
            email,
        )
        if (
            account is None
            or password_hash is None
            or not await asyncio.to_thread(
                verify_password,
                password,
                password_hash,
            )
        ):
            return None
        return account

    async def get_by_name(self, name: str, password: str) -> MaybeAccount:
        Assertion(name).must_be(str)
        if not Assertion(password).should_be(str) or not password.strip():
            raise ValueError('A password is required to load an account')

        account, password_hash = await get_account_with_password_by_name(name)
        if (
            account is None
            or password_hash is None
            or not await asyncio.to_thread(
                verify_password,
                password,
                password_hash,
            )
        ):
            return None
        return account

    async def create(self, account: Account, password: str) -> Account:
        Assertion(account).must_be(Account)
        if not isinstance(password, str) or not password.strip():
            raise ValueError('A password is required to create an account')

        try:
            password_hash: str = await asyncio.to_thread(
                hash_password,
                password,
            )
            return await persist_account(account, password_hash)
        except AccountAlreadyExistsError as e:
            raise AccountAlreadyExistsError(str(account.email)) from e

    async def update(self, account: Account) -> Account:
        Assertion(account).must_be(Account)
        if account.account_id is None:
            raise ValueError(
                'A persisted account UUID is required to update an account'
            )
        updated: MaybeAccount = await persist_account_update(account)
        if updated is None:
            raise AccountNotFoundError(str(account.account_id))
        return updated


# ================================================== #
# ACCOUNT FEATURES                                   #
# ================================================== #

repository: AccountRepository = SQLiteAccountRepository()

async def get_emails() -> list[str]:
    return [str(account.email) for account in await repository.get_everyone()]

async def get_names() -> list[str]:
    return [account.name for account in await repository.get_everyone()]

async def get_watchlist() -> set[str]:
    return {
        item.symbol
        for account in await repository.get_everyone()
        for item in account.watchlist
        if item is not None
    }

async def get_everyone() -> list[Account]:
    return await repository.get_everyone()

async def get_by_id(account_id: UUID | str) -> MaybeAccount:
    return await repository.get_by_id(account_id)

async def get_by_email(email: str, password: str) -> MaybeAccount:
    return await repository.get_by_email(email, password)

async def get_by_name(name: str, password: str) -> MaybeAccount:
    return await repository.get_by_name(name, password)

async def get_by_email_or_name(
    *,
    email: str | None = None,
    name: str | None = None,
    password: str,
) -> MaybeAccount:
    Assertion(email).must_be(str, None)
    Assertion(name).must_be(str, None)
    Assertion(password).must_be(str)

    if email is not None:
        account: MaybeAccount = await get_by_email(email, password)
        if account is not None:
            return account
    if name is not None:
        return await get_by_name(name, password)
    
    return None

async def create_account(account: Account, password: str) -> Account:
    return await repository.create(account, password)

async def update_account(account: Account) -> Account:
    return await repository.update(account)


async def change_password(
    account_id: UUID | str,
    current_password: str,
    new_password: str,
) -> bool:
    if not current_password or not new_password:
        raise ValueError('Current and new passwords are required')

    account, current_hash = await get_account_with_password(account_id)
    if account is None or current_hash is None:
        return False
    does_password_match: bool = await asyncio.to_thread(
        verify_password,
        current_password,
        current_hash,
    )
    if not does_password_match:
        return False

    password_hash: str = await asyncio.to_thread(
        hash_password,
        new_password,
    )

    return await persist_password_hash(
        account_id,
        password_hash,
    )


async def add_watchlist_item(account: Account, item: WatchlistItem) -> Account:
    Assertion(account).must_be(Account)
    Assertion(item).must_be(WatchlistItem)
    if any(
        current_item is not None and current_item.symbol == item.symbol
        for current_item in account.watchlist
    ):
        raise ValueError(f'{item.symbol} is already in the watchlist')
    account.watchlist.append(item)
    return await update_account(account)


async def remove_watchlist_item(account: Account, symbol: str) -> Account:
    Assertion(account).must_be(Account)
    Assertion(symbol).must_be(str)
    normalized_symbol: str = symbol.strip().upper()
    for index, item in enumerate(account.watchlist):
        if item is not None and item.symbol == normalized_symbol:
            del account.watchlist[index]
            return await update_account(account)
    raise ValueError(f'{normalized_symbol} is not in the watchlist')


async def add_trade(
    account: Account,
    action: Literal['BUY', 'SELL'],
    ticker: str,
    region: str,
    currency: str,
    price: float,
    quantity: int,
    date: str,
) -> Account:
    Assertion(account).must_be(Account)
    if action not in {'BUY', 'SELL'}:
        raise ValueError(f'Unsupported portfolio action: {action!r}')

    normalized_ticker: str = ticker.strip().upper()
    normalized_region: str = region.strip().upper()
    normalized_currency: str = currency.strip().upper()
    stock: Stock | None = next(
        (
            current_stock
            for current_stock in account.portfolio
            if current_stock is not None
            and current_stock.ticker == normalized_ticker
            and current_stock.region == normalized_region
            and current_stock.currency == normalized_currency
        ),
        None,
    )
    if stock is None:
        stock = Stock(
            ticker=normalized_ticker,
            region=normalized_region,
            currency=normalized_currency,
            actions=[],
        )
        account.portfolio.append(stock)

    stock.actions.append(
        Action(
            action=action,
            price=price,
            quantity=quantity,
            date=date,
        )
    )
    return await update_account(account)

def count_shares[A: StrEnum](account: Account, sum_mapping: dict[A, int] | None = None) -> dict[str, int]:
    Assertion(account).must_be(Account)
    Assertion(sum_mapping).must_be(dict, None)

    result: dict[str, int] = {}
    mapping: dict[A, int] | dict[str, int] = (
        sum_mapping or { 'BUY': 1, 'SELL': -1 }
    )
    for share in account.portfolio:
        if share is None:
            continue
        result[share.ticker] = sum(
            action.quantity * mapping[action.action]
            for action in share.actions
        )
    
    return result


def has_positive_position(account: Account, ticker: Ticker) -> bool:
    Assertion(account).must_be(Account)
    Assertion(ticker).must_be(Ticker)

    target_symbol: str = ticker.symbol.upper()
    target_region: str = ticker.region.upper()
    if target_region == 'USD':
        target_region = 'US'
    net_shares: int = 0
    for holding in account.portfolio:
        if holding is None:
            continue
        symbol: str = holding.ticker.strip().upper()
        region: str = holding.region.strip().upper()
        if '.' in symbol:
            symbol, region = symbol.split('.', maxsplit=1)
        if region == 'USD':
            region = 'US'
        if symbol != target_symbol or region != target_region:
            continue
        net_shares += sum(
            action.quantity * (1 if action.action == 'BUY' else -1)
            for action in holding.actions
        )
    return net_shares > 0
