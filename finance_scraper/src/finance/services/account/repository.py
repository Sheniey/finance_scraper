
import asyncio
from enum import StrEnum
from typing import Literal, Protocol
from designkit.behavioral.typing import Assertion
from uuid import UUID

from datatypes.ticker import Ticker

from finance.services.account.exceptions import (
    AccountVaultException,
    AccountAlreadyExistsError,
    AccountNotFoundError,
    VaultEnvelopeError,
    VaultLockedError
)
from finance.services.account.models import Account, Action, Stock, WatchlistItem
from finance.services.account.db import (
    create_account as persist_account,
    get_account_by_id as load_account_by_id,
    get_account_with_password,
    get_account_with_password_by_email,
    get_account_with_password_by_name,
    get_account_umk_envelope,
    load_account_llm_key_envelopes,
    load_accounts,
    delete_account_llm_key as persist_llm_key_delete,
    replace_account_umk_and_clear_llm_keys,
    set_account_umk_envelope_if_missing,
    update_account_password_and_umk,
    upsert_account_llm_key_envelope,
    update_account as persist_account_update
)
from finance_core.security import hash_password, verify_password
from finance.services.account.vault import (
    LLMProvider,
    decrypt_provider_key,
    encrypt_provider_key,
    generate_umk,
    normalize_llm_provider,
    unwrap_umk,
    wrap_umk,
    vault_sessions
)


# ================================================== #
# TYPE ALIASES                                       #
# ================================================== #

type MaybeAccount = Account | None
type PasswordHash = str


# ================================================== #
# HELPER FUNCTIONS                                   #
# ================================================== #

async def _unlock_account_vault(account_id: UUID | str, password: str) -> bytes:
    encrypted_umk: str | None = await get_account_umk_envelope(account_id)
    umk: bytes
    if encrypted_umk is None:
        umk = generate_umk()
        encrypted_umk = await asyncio.to_thread(
            wrap_umk,
            umk,
            password,
            account_id,
        )
        was_stored: bool = await set_account_umk_envelope_if_missing(
            account_id,
            encrypted_umk,
        )

        if not was_stored:
            encrypted_umk = await get_account_umk_envelope(account_id)
            if encrypted_umk is None:
                raise AccountNotFoundError(str(account_id))
            umk = await asyncio.to_thread(
                unwrap_umk,
                encrypted_umk,
                password,
                account_id,
            )
    else:
        umk = await asyncio.to_thread(
            unwrap_umk,
            encrypted_umk,
            password,
            account_id,
        )

    vault_sessions.unlock(account_id, umk)
    return umk


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
        await _unlock_account_vault(
            account.account_id or account.id,
            password,
        )
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
        await _unlock_account_vault(
            account.account_id or account.id,
            password,
        )
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
            account_id: UUID = account.account_id or account.id
            umk: bytes = generate_umk()
            encrypted_umk: str = await asyncio.to_thread(
                wrap_umk,
                umk,
                password,
                account_id,
            )
            return await persist_account(
                account,
                password_hash,
                encrypted_umk,
            )
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
    password: str
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
    new_password: str
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
    encrypted_umk: str | None = await get_account_umk_envelope(account_id)
    if encrypted_umk is None:
        umk: bytes = generate_umk()
    else:
        umk = await asyncio.to_thread(
            unwrap_umk,
            encrypted_umk,
            current_password,
            account_id,
        )
    
    new_encrypted_umk: str = await asyncio.to_thread(
        wrap_umk,
        umk,
        new_password,
        account_id,
    )
    was_changed: bool = await update_account_password_and_umk(
        account_id,
        password_hash,
        new_encrypted_umk,
    )

    if was_changed:
        vault_sessions.lock(account_id)
    return was_changed


async def get_account_llm_keys(account_id: UUID | str) -> dict[LLMProvider, str]:
    encrypted_keys: dict[str, str] = await load_account_llm_key_envelopes(account_id)
    if not encrypted_keys:
        return {}

    umk: bytes | None = vault_sessions.get(account_id)
    if umk is None:
        raise VaultLockedError('The account vault must be unlocked before using its LLM keys.')
    
    decrypted_keys: dict[LLMProvider, str] = {}
    for provider_name, envelope in encrypted_keys.items():
        provider: LLMProvider = normalize_llm_provider(provider_name)
        if provider.value != provider_name:
            raise VaultEnvelopeError('An account LLM key uses an unsupported provider identifier.')
        
        decrypted_keys[provider] = decrypt_provider_key(
            envelope,
            umk,
            account_id,
            provider,
        )
    return decrypted_keys

async def get_account_llm_key_providers(account_id: UUID | str) -> list[LLMProvider]:
    encrypted_keys: dict[str, str] = await load_account_llm_key_envelopes(account_id)
    return [
        normalize_llm_provider(provider)
        for provider in encrypted_keys
    ]

async def set_account_llm_key(account_id: UUID | str, provider: str | LLMProvider, api_key: str) -> None:
    normalized_provider: LLMProvider = normalize_llm_provider(provider)
    umk: bytes | None = vault_sessions.get(account_id)
    if umk is None:
        raise VaultLockedError('The account vault must be unlocked before setting an LLM key.')
    
    encrypted_value: str = encrypt_provider_key(
        api_key,
        umk,
        account_id,
        normalized_provider,
    )

    await upsert_account_llm_key_envelope(
        account_id,
        normalized_provider.value,
        encrypted_value,
    )

async def remove_account_llm_key(account_id: UUID | str, provider: str | LLMProvider) -> bool:
    normalized_provider: LLMProvider = normalize_llm_provider(provider)
    if vault_sessions.get(account_id) is None:
        raise VaultLockedError('The account vault must be unlocked before removing an LLM key.')
    
    return await persist_llm_key_delete(
        account_id,
        normalized_provider.value,
    )

async def regenerate_account_umk(account_id: UUID | str, password: str, *, confirmed: bool) -> bool:
    if not confirmed:
        raise ValueError('Regenerating the UMK requires explicit confirmation.')

    account, password_hash = await get_account_with_password(account_id)
    if account is None or password_hash is None:
        return False
    
    does_password_match: bool = await asyncio.to_thread(
        verify_password,
        password,
        password_hash,
    )
    if not does_password_match:
        return False

    umk: bytes = generate_umk()
    encrypted_umk: str = await asyncio.to_thread(
        wrap_umk,
        umk,
        password,
        account_id,
    )

    was_replaced: bool = await replace_account_umk_and_clear_llm_keys(
        account_id,
        encrypted_umk,
    )
    if was_replaced:
        vault_sessions.unlock(account_id, umk)
    return was_replaced

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
    date: str
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
    mapping: dict[A, int] | dict[str, int] = sum_mapping or { 'BUY': 1, 'SELL': -1 }
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
