"""Shared async Turso/libSQL schema and lookup helpers."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from finance.config import (
    DB_AUTH_TOKEN,
    DB_LOCAL_PATH,
    DB_LOCATION,
)
from finance.services.database import (
    AsyncDatabaseResult,
    get_turso_sync_pool,
)
from finance.services.database.exceptions import (
    DatabaseConfigurationError,
    DatabaseSyncError,
)

if TYPE_CHECKING:
    from finance.services.account.models import Account


logger: logging.Logger = logging.getLogger(__name__)


# ================================================== #
# TYPES                                              #
# ================================================== #

class AsyncDatabaseExecutor(Protocol):
    async def execute(
        self,
        statement: str,
        parameters: object = None,
    ) -> AsyncDatabaseResult:
        ...


# ================================================== #
# DATABASE CONNECTIONS                               #
# ================================================== #

DATABASE_PATH: str | Path = DB_LOCAL_PATH


# ================================================== #
# SHARED DATABASE SCHEMA                             #
# ================================================== #

async def create_schema(connection: AsyncDatabaseExecutor) -> None:
    await connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS languages (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
        '''
    )
    await connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS tickers (
            ticker_id INTEGER PRIMARY KEY,
            ticker TEXT NOT NULL,
            region TEXT NOT NULL,
            UNIQUE (ticker, region)
        )
        '''
    )
    await connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS currencies (
            currency_id INTEGER PRIMARY KEY,
            currency TEXT NOT NULL UNIQUE
        )
        '''
    )


async def initialize_database(
    database: str | Path = DATABASE_PATH,
    *,
    remote_url: str = DB_LOCATION,
    auth_token: str | None = DB_AUTH_TOKEN,
) -> None:
    """Verify shared tables were provisioned before application startup."""

    pool = await get_turso_sync_pool(
        database,
        remote_url=remote_url,
        auth_token=auth_token,
    )
    try:
        await pool.pull()
    except DatabaseSyncError as e:
        logger.warning(
            'Initial Turso pull failed; checking the local replica: %s',
            e,
        )
    async with pool.connection() as connection:
        result: AsyncDatabaseResult = await connection.execute(
            '''
            SELECT name
            FROM sqlite_schema
            WHERE type = 'table'
            ''',
        )
        available_tables: set[str] = {
            str(row['name'])
            for row in result.fetchall()
        }

    required_tables: set[str] = {'languages', 'tickers', 'currencies'}
    if not required_tables.issubset(available_tables):
        raise DatabaseConfigurationError(
            'The shared Turso Sync schema is incomplete; '
            'provision it through the approved migration workflow.',
        )


# ================================================== #
# SHARED TABLE HELPERS                               #
# ================================================== #

def _normalized_value(value: str, field_name: str) -> str:
    normalized: str = value.strip().upper()
    if not normalized:
        raise ValueError(f'{field_name} must not be blank')
    return normalized


async def ensure_language(
    connection: AsyncDatabaseExecutor,
    account: Account,
) -> None:
    await connection.execute(
        '''
        INSERT INTO languages (code, name)
        VALUES (?, ?)
        ON CONFLICT(code) DO NOTHING
        ''',
        (account.language.code, account.language.name),
    )


async def get_or_create_ticker(
    connection: AsyncDatabaseExecutor,
    ticker: str,
    region: str,
) -> int:
    normalized_ticker: str = _normalized_value(ticker, 'ticker')
    normalized_region: str = _normalized_value(region, 'region')
    row: dict[str, object] | None = (
        await connection.execute(
            '''
            INSERT INTO tickers (ticker, region)
            VALUES (?, ?)
            ON CONFLICT(ticker, region)
            DO UPDATE SET ticker = excluded.ticker
            RETURNING ticker_id
            ''',
            (normalized_ticker, normalized_region),
        )
    ).fetchone()

    if row is None:
        raise RuntimeError(
            f'Could not resolve ticker {normalized_ticker}.{normalized_region}',
        )
    return int(row['ticker_id'])


async def get_or_create_currency(
    connection: AsyncDatabaseExecutor,
    currency: str,
) -> int:
    normalized_currency: str = _normalized_value(currency, 'currency')
    row: dict[str, object] | None = (
        await connection.execute(
            '''
            INSERT INTO currencies (currency)
            VALUES (?)
            ON CONFLICT(currency)
            DO UPDATE SET currency = excluded.currency
            RETURNING currency_id
            ''',
            (normalized_currency,),
        )
    ).fetchone()

    if row is None:
        raise RuntimeError(f'Could not resolve currency {normalized_currency}')
    return int(row['currency_id'])


__all__: list[str] = [
    'DATABASE_PATH',
    'AsyncDatabaseExecutor',
    'create_schema',
    'ensure_language',
    'get_or_create_currency',
    'get_or_create_ticker',
    'initialize_database',
]
