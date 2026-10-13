"""Async normalized Turso/libSQL persistence for application accounts."""

import asyncio
import logging
from pathlib import Path
from threading import RLock
from collections import defaultdict
from collections.abc import AsyncIterator, Iterable, Sequence
from contextlib import asynccontextmanager
from typing import Any, Literal
from uuid import UUID, uuid4

from finance.config import (
    DB_AUTH_TOKEN,
    DB_LOCAL_PATH,
    DB_LOCATION,
    DB_POOL_SIZE,
    DB_POOL_TIMEOUT,
)
from finance.services.account.exceptions import (
    AccountAlreadyExistsError,
    AccountSchemaException,
)
from finance.services.account.models import Account, Action, Stock, WatchlistItem
from finance.services.database import (
    AsyncDatabaseConnection,
    DatabaseIntegrityError,
    DatabaseSyncError,
    LibSQLRow,
    get_database_pool,
    get_turso_sync_pool,
)
from finance.services.database.repository import (
    AsyncDatabaseExecutor,
    create_schema,
    ensure_language,
    get_or_create_currency,
    get_or_create_ticker,
)


# ================================================== #
# CONFIGURATION AND STATE                            #
# ================================================== #

logger: logging.Logger = logging.getLogger(__name__)
DATABASE_PATH: str | Path = DB_LOCAL_PATH
REMOTE_URL: str = DB_LOCATION
REQUIRE_SYNC_MARKER: bool = True
_LANGUAGE_STYLES: tuple[str, ...] = (
    'friendly',
    'professional',
    'technical',
)
_REPORT_MODES: tuple[str, ...] = (
    'classic',
    'full',
    'custom',
    'growth',
    'validation',
    'info',
)
type AccountId = str
_ACCOUNT_CHILD_TABLES: tuple[str, ...] = (
    'action_history',
    'account_custom_reports',
    'account_watchlist',
)
_ACCOUNT_MIGRATION_SUFFIX: str = '_uuid_migration'
_ACCOUNT_ID_MAP_TABLE: str = '_account_id_uuid_migration_map'
_ACCOUNT_CHILD_COLUMNS: dict[str, tuple[str, ...]] = {
    'action_history': (
        'action_id',
        'account_id',
        'ticker_id',
        'currency_id',
        'action',
        'quantity',
        'price',
        'timestamp',
    ),
    'account_custom_reports': (
        'account_id',
        'position',
        'metric',
    ),
    'account_watchlist': (
        'account_id',
        'position',
        'is_empty',
        'ticker_id',
        'rendering_mode',
        'llm_explanation',
    ),
}
_schema_ready: set[str] = set()
_schema_locks: dict[str, asyncio.Lock] = {}
_schema_registry_lock: RLock = RLock()


def _database_key() -> str:
    return str(Path(DATABASE_PATH).expanduser().resolve())


def _schema_lock(key: str) -> asyncio.Lock:
    with _schema_registry_lock:
        lock: asyncio.Lock | None = _schema_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _schema_locks[key] = lock
        return lock


async def _pool():
    if REMOTE_URL:
        return await get_turso_sync_pool(
            DATABASE_PATH,
            remote_url=REMOTE_URL,
            auth_token=DB_AUTH_TOKEN,
            require_sync_marker=REQUIRE_SYNC_MARKER,
            size=DB_POOL_SIZE,
            acquire_timeout=DB_POOL_TIMEOUT,
        )
    return await get_database_pool(
        DATABASE_PATH,
        auth_token=None,
        size=DB_POOL_SIZE,
        acquire_timeout=DB_POOL_TIMEOUT,
    )


@asynccontextmanager
async def _connection() -> AsyncIterator[AsyncDatabaseConnection]:
    pool = await _pool()
    async with pool.connection() as connection:
        yield connection


# ================================================== #
# SCHEMA                                             #
# ================================================== #

async def _table_exists(
    connection: AsyncDatabaseExecutor,
    table_name: str,
) -> bool:
    row: LibSQLRow | None = (
        await connection.execute(
            '''
            SELECT 1
            FROM sqlite_schema
            WHERE type = 'table' AND name = ?
            LIMIT 1
            ''',
            (table_name,),
        )
    ).fetchone()
    return row is not None


async def _table_columns(
    connection: AsyncDatabaseExecutor,
    table_name: str,
) -> dict[str, LibSQLRow]:
    return {
        str(row['name']): row
        for row in (
            await connection.execute(
                f'PRAGMA table_info({table_name})',
            )
        ).fetchall()
    }


async def _account_schema_is_current(
    connection: AsyncDatabaseExecutor,
) -> bool:
    if not await _table_exists(connection, 'accounts'):
        return False

    columns: dict[str, LibSQLRow] = await _table_columns(
        connection,
        'accounts',
    )
    required_columns: set[str] = {
        'account_id',
        'email',
        'name',
        'role',
        'language_code',
        'language_style',
        'password_hash',
    }
    if not required_columns.issubset(columns):
        return False

    account_id_column: LibSQLRow = columns['account_id']
    role_column: LibSQLRow = columns['role']
    if (
        str(account_id_column['type']).upper() != 'TEXT'
        or int(account_id_column['notnull']) != 1
        or int(account_id_column['pk']) != 1
        or str(role_column['type']).upper() != 'TEXT'
        or int(role_column['notnull']) != 1
    ):
        return False

    for table_name in _ACCOUNT_CHILD_TABLES:
        if not await _table_exists(connection, table_name):
            continue
        child_columns: dict[str, LibSQLRow] = await _table_columns(
            connection,
            table_name,
        )
        account_id_column = child_columns.get('account_id')
        if (
            account_id_column is None
            or str(account_id_column['type']).upper() != 'TEXT'
            or int(account_id_column['notnull']) != 1
        ):
            return False

    return True


async def _create_account_tables(
    connection: AsyncDatabaseExecutor,
    table_suffix: str = '',
) -> None:
    accounts_table: str = f'accounts{table_suffix}'
    action_history_table: str = f'action_history{table_suffix}'
    custom_reports_table: str = f'account_custom_reports{table_suffix}'
    watchlist_table: str = f'account_watchlist{table_suffix}'

    await connection.execute(
        f'''
        CREATE TABLE IF NOT EXISTS {accounts_table} (
            account_id TEXT NOT NULL PRIMARY KEY,
            email TEXT NOT NULL COLLATE NOCASE UNIQUE,
            name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            language_code TEXT NOT NULL
                REFERENCES languages(code),
            language_style TEXT NOT NULL
                CHECK (language_style IN (
                    '{_LANGUAGE_STYLES[0]}',
                    '{_LANGUAGE_STYLES[1]}',
                    '{_LANGUAGE_STYLES[2]}'
                )),
            password_hash TEXT NOT NULL
        )
        '''
    )
    await connection.execute(
        f'''
        CREATE TABLE IF NOT EXISTS {action_history_table} (
            action_id INTEGER PRIMARY KEY,
            account_id TEXT NOT NULL
                REFERENCES {accounts_table}(account_id) ON DELETE CASCADE,
            ticker_id INTEGER NOT NULL
                REFERENCES tickers(ticker_id),
            currency_id INTEGER NOT NULL
                REFERENCES currencies(currency_id),
            action TEXT NOT NULL CHECK (action IN ('BUY', 'SELL')),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            price REAL NOT NULL CHECK (price >= 0),
            timestamp DATETIME NOT NULL
        )
        '''
    )
    await connection.execute(
        f'''
        CREATE TABLE IF NOT EXISTS {custom_reports_table} (
            account_id TEXT NOT NULL
                REFERENCES {accounts_table}(account_id) ON DELETE CASCADE,
            position INTEGER NOT NULL,
            metric TEXT NOT NULL,
            PRIMARY KEY (account_id, position)
        )
        '''
    )
    await connection.execute(
        f'''
        CREATE TABLE IF NOT EXISTS {watchlist_table} (
            account_id TEXT NOT NULL
                REFERENCES {accounts_table}(account_id) ON DELETE CASCADE,
            position INTEGER NOT NULL CHECK (position >= 0),
            is_empty INTEGER NOT NULL DEFAULT 0
                CHECK (is_empty IN (0, 1)),
            ticker_id INTEGER REFERENCES tickers(ticker_id),
            rendering_mode TEXT NOT NULL DEFAULT 'classic'
                CHECK (rendering_mode IN (
                    '{_REPORT_MODES[0]}',
                    '{_REPORT_MODES[1]}',
                    '{_REPORT_MODES[2]}',
                    '{_REPORT_MODES[3]}',
                    '{_REPORT_MODES[4]}',
                    '{_REPORT_MODES[5]}'
                )),
            llm_explanation INTEGER NOT NULL DEFAULT 0
                CHECK (llm_explanation IN (0, 1)),
            PRIMARY KEY (account_id, position),
            CHECK (
                (is_empty = 1 AND ticker_id IS NULL)
                OR (is_empty = 0 AND ticker_id IS NOT NULL)
            )
        )
        '''
    )


async def create_account_schema(
    connection: AsyncDatabaseExecutor,
) -> None:
    await _create_account_tables(connection)
    await connection.execute(
        '''
        CREATE INDEX IF NOT EXISTS idx_accounts_name_nocase
        ON accounts(name COLLATE NOCASE)
        '''
    )
    await connection.execute(
        '''
        CREATE INDEX IF NOT EXISTS idx_action_history_account_action
        ON action_history(account_id, action_id)
        '''
    )


async def _validate_legacy_account_schema(
    connection: AsyncDatabaseExecutor,
) -> dict[str, LibSQLRow]:
    account_columns: dict[str, LibSQLRow] = await _table_columns(
        connection,
        'accounts',
    )
    legacy_account_columns: set[str] = {
        'account_id',
        'email',
        'name',
        'language_code',
        'language_style',
        'password_hash',
    }
    if (
        not legacy_account_columns.issubset(account_columns)
        or set(account_columns) - legacy_account_columns - {'role'}
    ):
        raise AccountSchemaException(
            'The account migration only supports the known integer-ID '
            'account schema; no data was changed.'
        )

    account_id_column: LibSQLRow = account_columns['account_id']
    if (
        str(account_id_column['type']).upper() != 'INTEGER'
        or int(account_id_column['pk']) != 1
    ):
        raise AccountSchemaException(
            'The account schema is neither the supported integer-ID schema '
            'nor the current UUID schema; no data was changed.'
        )

    role_column: LibSQLRow | None = account_columns.get('role')
    if (
        role_column is not None
        and str(role_column['type']).upper() != 'TEXT'
    ):
        raise AccountSchemaException(
            'The legacy role column must use TEXT; no data was changed.'
        )

    for table_name, expected_columns in _ACCOUNT_CHILD_COLUMNS.items():
        if not await _table_exists(connection, table_name):
            continue
        child_columns: dict[str, LibSQLRow] = await _table_columns(
            connection,
            table_name,
        )
        if set(child_columns) != set(expected_columns):
            raise AccountSchemaException(
                f'The account migration does not recognize table '
                f'{table_name!r}; no data was changed.'
            )
        account_id_column = child_columns['account_id']
        if str(account_id_column['type']).upper() != 'INTEGER':
            raise AccountSchemaException(
                f'Table {table_name!r} does not use integer account IDs; '
                'no data was changed.'
            )

    return account_columns


async def _table_row_count(
    connection: AsyncDatabaseExecutor,
    table_name: str,
) -> int:
    row: LibSQLRow | None = (
        await connection.execute(
            f'SELECT COUNT(*) AS row_count FROM {table_name}',
        )
    ).fetchone()
    if row is None:
        raise RuntimeError(f'Could not count rows in table {table_name!r}')
    return int(row['row_count'])


async def _assert_account_foreign_keys(
    connection: AsyncDatabaseExecutor,
    table_names: Sequence[str],
) -> None:
    for table_name in table_names:
        violations: list[LibSQLRow] = (
            await connection.execute(
                f'PRAGMA foreign_key_check({table_name})',
            )
        ).fetchall()
        if violations:
            raise AccountSchemaException(
                f'Foreign-key validation failed for {table_name!r}: '
                f'{violations[0]!r}.'
            )


async def _migrate_integer_account_schema(
    connection: AsyncDatabaseExecutor,
) -> None:
    account_columns: dict[str, LibSQLRow] = (
        await _validate_legacy_account_schema(connection)
    )
    staged_tables: tuple[str, ...] = (
        f'accounts{_ACCOUNT_MIGRATION_SUFFIX}',
        *(
            f'{table_name}{_ACCOUNT_MIGRATION_SUFFIX}'
            for table_name in _ACCOUNT_CHILD_TABLES
        ),
    )
    for table_name in (*staged_tables, _ACCOUNT_ID_MAP_TABLE):
        if await _table_exists(connection, table_name):
            raise AccountSchemaException(
                f'An account migration staging table {table_name!r} already '
                'exists; inspect the database before retrying.'
            )

    await connection.execute(
        f'''
        CREATE TABLE {_ACCOUNT_ID_MAP_TABLE} (
            old_account_id INTEGER PRIMARY KEY,
            new_account_id TEXT NOT NULL UNIQUE
        )
        '''
    )
    old_account_rows: list[LibSQLRow] = (
        await connection.execute(
            'SELECT account_id FROM accounts ORDER BY account_id',
        )
    ).fetchall()
    for row in old_account_rows:
        await connection.execute(
            f'''
            INSERT INTO {_ACCOUNT_ID_MAP_TABLE} (
                old_account_id, new_account_id
            )
            VALUES (?, ?)
            ''',
            (int(row['account_id']), str(uuid4())),
        )

    await _create_account_tables(
        connection,
        _ACCOUNT_MIGRATION_SUFFIX,
    )
    role_expression: str = (
        "COALESCE(source.role, 'user')"
        if 'role' in account_columns
        else "'user'"
    )
    await connection.execute(
        f'''
        INSERT INTO accounts{_ACCOUNT_MIGRATION_SUFFIX} (
            account_id, email, name, role, language_code,
            language_style, password_hash
        )
        SELECT id_map.new_account_id, source.email, source.name,
               {role_expression}, source.language_code,
               source.language_style, source.password_hash
        FROM accounts AS source
        JOIN {_ACCOUNT_ID_MAP_TABLE} AS id_map
          ON id_map.old_account_id = source.account_id
        '''
    )

    for table_name, columns in _ACCOUNT_CHILD_COLUMNS.items():
        if not await _table_exists(connection, table_name):
            continue
        column_list: str = ', '.join(columns)
        selected_columns: str = ', '.join(
            (
                'id_map.new_account_id'
                if column == 'account_id'
                else f'source.{column}'
            )
            for column in columns
        )
        await connection.execute(
            f'''
            INSERT INTO {table_name}{_ACCOUNT_MIGRATION_SUFFIX} (
                {column_list}
            )
            SELECT {selected_columns}
            FROM {table_name} AS source
            JOIN {_ACCOUNT_ID_MAP_TABLE} AS id_map
              ON id_map.old_account_id = source.account_id
            '''
        )

    source_tables: tuple[str, ...] = (
        'accounts',
        *_ACCOUNT_CHILD_TABLES,
    )
    for source_table, staged_table in zip(
        source_tables,
        staged_tables,
        strict=True,
    ):
        if not await _table_exists(connection, source_table):
            continue
        source_count: int = await _table_row_count(
            connection,
            source_table,
        )
        staged_count: int = await _table_row_count(
            connection,
            staged_table,
        )
        if source_count != staged_count:
            raise AccountSchemaException(
                f'Account migration row count mismatch for '
                f'{source_table!r}; no source tables were replaced.'
            )

    await _assert_account_foreign_keys(connection, staged_tables)

    for table_name in _ACCOUNT_CHILD_TABLES:
        if await _table_exists(connection, table_name):
            await connection.execute(f'DROP TABLE {table_name}')
    await connection.execute('DROP TABLE accounts')
    await connection.execute(
        f'''
        ALTER TABLE accounts{_ACCOUNT_MIGRATION_SUFFIX}
        RENAME TO accounts
        '''
    )
    for table_name in _ACCOUNT_CHILD_TABLES:
        await connection.execute(
            f'''
            ALTER TABLE {table_name}{_ACCOUNT_MIGRATION_SUFFIX}
            RENAME TO {table_name}
            '''
        )
    await connection.execute(f'DROP TABLE {_ACCOUNT_ID_MAP_TABLE}')
    await create_account_schema(connection)
    await _assert_account_foreign_keys(
        connection,
        ('accounts', *_ACCOUNT_CHILD_TABLES),
    )


async def migrate_account_schema() -> bool:
    """Migrate legacy integer account IDs to UUIDs without losing relations."""

    key: str = _database_key()
    pool = await _pool()
    if pool.is_turso_sync:
        raise AccountSchemaException(
            'Account schema changes must be applied through the approved '
            'Turso schema migration, not the runtime sync token.'
        )
    migrated: bool = False
    async with pool.transaction() as connection:
        if not await _table_exists(connection, 'accounts'):
            return False
        if await _account_schema_is_current(connection):
            return False
        await _migrate_integer_account_schema(connection)
        if not await _account_schema_is_current(connection):
            raise AccountSchemaException(
                'The account migration did not produce the current schema.'
            )
        migrated = True

    if migrated:
        _schema_ready.add(key)
    return migrated


async def initialize_account_database() -> None:
    """Initialize a fresh local database or verify a provisioned replica."""

    key: str = _database_key()
    if key in _schema_ready:
        return

    async with _schema_lock(key):
        if key in _schema_ready:
            return
        pool = await _pool()
        if pool.is_turso_sync:
            try:
                await pool.pull()
            except DatabaseSyncError as e:
                logger.warning(
                    'Initial Turso pull failed; checking the local replica: %s',
                    e,
                )

        required_tables: tuple[str, ...] = (
            'languages',
            'tickers',
            'currencies',
            'accounts',
            *_ACCOUNT_CHILD_TABLES,
        )
        if not pool.is_turso_sync:
            async with pool.transaction() as connection:
                existing_tables: list[str] = [
                    table_name
                    for table_name in required_tables
                    if await _table_exists(connection, table_name)
                ]
                if not existing_tables:
                    await create_schema(connection)
                    await create_account_schema(connection)
                elif len(existing_tables) != len(required_tables):
                    missing_tables: list[str] = [
                        table_name
                        for table_name in required_tables
                        if table_name not in existing_tables
                    ]
                    raise AccountSchemaException(
                        'The local account database is incomplete; missing '
                        f'tables: {", ".join(missing_tables)}.'
                    )

            async with pool.connection() as connection:
                is_current_schema: bool = await _account_schema_is_current(
                    connection,
                )
            if not is_current_schema:
                await migrate_account_schema()

        async with pool.connection() as connection:
            missing_tables: list[str] = [
                table_name
                for table_name in required_tables
                if not await _table_exists(connection, table_name)
            ]
            if missing_tables:
                raise AccountSchemaException(
                    'The local Turso Sync replica is missing required tables; '
                    'run the database bootstrap migration.'
                )
            if not await _account_schema_is_current(connection):
                raise AccountSchemaException(
                    'The account database schema does not match the UUID '
                    'model. Migrate the source database before syncing it.'
                )
            await _assert_account_foreign_keys(
                connection,
                ('accounts', *_ACCOUNT_CHILD_TABLES),
            )
        _schema_ready.add(key)


async def reset_account_schema() -> None:
    """Rebuild account tables for tests or an explicit migration."""

    key: str = _database_key()
    pool = await _pool()
    if pool.is_turso_sync:
        raise AccountSchemaException(
            'Account tables cannot be reset in a Turso Sync database.'
        )
    async with pool.transaction() as connection:
        for table_name in (
            'account_watchlist',
            'account_custom_reports',
            'action_history',
            'accounts',
        ):
            await connection.execute(f'DROP TABLE IF EXISTS {table_name}')
        await create_schema(connection)
        await create_account_schema(connection)
    _schema_ready.add(key)


# ================================================== #
# WRITE HELPERS                                       #
# ================================================== #

async def insert_portfolio(
    connection: AsyncDatabaseExecutor,
    account_id: AccountId,
    account: Account,
) -> None:
    action_values: list[tuple[Any, ...]] = []
    for stock in account.portfolio:
        if stock is None:
            continue
        ticker_id: int = await get_or_create_ticker(
            connection,
            stock.ticker,
            stock.region,
        )
        currency_id: int = await get_or_create_currency(
            connection,
            stock.currency,
        )
        action_values.extend(
            (
                account_id,
                ticker_id,
                currency_id,
                action.action,
                action.quantity,
                action.price,
                action.date,
            )
            for action in stock.actions
        )

    if not action_values:
        return
    placeholders: str = ', '.join(
        '(?, ?, ?, ?, ?, ?, ?)' for _ in action_values
    )
    flattened: tuple[Any, ...] = tuple(
        value
        for row in action_values
        for value in row
    )
    await connection.execute(
        f'''
        INSERT INTO action_history (
            account_id, ticker_id, currency_id, action,
            quantity, price, timestamp
        )
        VALUES {placeholders}
        ''',
        flattened,
    )


async def insert_children(
    connection: AsyncDatabaseExecutor,
    account_id: AccountId,
    account: Account,
) -> None:
    if account.custom_report:
        report_values: list[tuple[Any, ...]] = [
            (account_id, position, metric)
            for position, metric in enumerate(account.custom_report)
        ]
        report_placeholders: str = ', '.join(
            '(?, ?, ?)' for _ in report_values
        )
        await connection.execute(
            f'''
            INSERT INTO account_custom_reports (account_id, position, metric)
            VALUES {report_placeholders}
            ''',
            tuple(value for row in report_values for value in row),
        )

    watchlist_values: list[tuple[Any, ...]] = []
    for position, item in enumerate(account.watchlist):
        if item is None:
            watchlist_values.append((account_id, position, 1, None, None, 0))
            continue
        ticker_id: int = await get_or_create_ticker(
            connection,
            item.ticker,
            item.region,
        )
        watchlist_values.append(
            (
                account_id,
                position,
                0,
                ticker_id,
                item.mode.value,
                int(item.llm_explanation),
            )
        )

    if watchlist_values:
        watchlist_placeholders: str = ', '.join(
            '(?, ?, ?, ?, ?, ?)' for _ in watchlist_values
        )
        await connection.execute(
            f'''
            INSERT INTO account_watchlist (
                account_id, position, is_empty, ticker_id,
                rendering_mode, llm_explanation
            )
            VALUES {watchlist_placeholders}
            ''',
            tuple(value for row in watchlist_values for value in row),
        )

    await insert_portfolio(connection, account_id, account)


async def _insert_account(
    connection: AsyncDatabaseExecutor,
    account: Account,
    password_hash: str,
) -> Account:
    await ensure_language(connection, account)
    account_uuid: UUID = account.account_id or account.id
    account_id: AccountId = str(account_uuid)
    await connection.execute(
        '''
        INSERT INTO accounts (
            account_id, email, name, role,
            language_code, language_style, password_hash
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            account_id,
            str(account.email),
            account.name,
            account.role,
            account.language.code,
            account.language.style,
            password_hash,
        ),
    )
    await insert_children(connection, account_id, account)
    persisted_account_id: UUID = UUID(account_id)
    return account.model_copy(
        update={
            'id': persisted_account_id,
            'account_id': persisted_account_id,
        },
    )


# ================================================== #
# ACCOUNT READ MODELS                                #
# ================================================== #

_ACCOUNT_COLUMNS: str = '''
    accounts.account_id,
    accounts.email,
    accounts.name,
    accounts.role,
    accounts.language_code,
    accounts.language_style,
    languages.name AS language_name
'''


def _placeholders(values: Sequence[AccountId]) -> str:
    return ', '.join('?' for _ in values)


async def _load_related(
    connection: AsyncDatabaseConnection,
    account_ids: Sequence[AccountId],
) -> tuple[list[LibSQLRow], list[LibSQLRow], list[LibSQLRow]]:
    if not account_ids:
        return [], [], []
    placeholders: str = _placeholders(account_ids)
    custom_reports, watchlists, actions = await connection.batch(
        [
            (
                f'''
                SELECT account_id, position, metric
                FROM account_custom_reports
                WHERE account_id IN ({placeholders})
                ORDER BY account_id, position
                ''',
                tuple(account_ids),
            ),
            (
                f'''
                SELECT account_watchlist.account_id,
                       account_watchlist.position,
                       account_watchlist.is_empty,
                       account_watchlist.rendering_mode,
                       account_watchlist.llm_explanation,
                       tickers.ticker,
                       tickers.region
                FROM account_watchlist
                LEFT JOIN tickers
                    ON tickers.ticker_id = account_watchlist.ticker_id
                WHERE account_watchlist.account_id IN ({placeholders})
                ORDER BY account_watchlist.account_id,
                         account_watchlist.position
                ''',
                tuple(account_ids),
            ),
            (
                f'''
                SELECT action_history.account_id,
                       action_history.ticker_id,
                       action_history.currency_id,
                       action_history.action,
                       action_history.quantity,
                       action_history.price,
                       action_history.timestamp,
                       tickers.ticker,
                       tickers.region,
                       currencies.currency
                FROM action_history
                JOIN tickers
                    ON tickers.ticker_id = action_history.ticker_id
                JOIN currencies
                    ON currencies.currency_id = action_history.currency_id
                WHERE action_history.account_id IN ({placeholders})
                ORDER BY action_history.account_id, action_history.action_id
                ''',
                tuple(account_ids),
            ),
        ]
    )
    return (
        custom_reports.fetchall(),
        watchlists.fetchall(),
        actions.fetchall(),
    )


def _account_from_parts(
    row: LibSQLRow,
    custom_rows: Iterable[LibSQLRow],
    watchlist_rows: Iterable[LibSQLRow],
    action_rows: Iterable[LibSQLRow],
) -> Account:
    custom_report: list[str] = [
        str(child['metric'])
        for child in custom_rows
    ]
    watchlist: list[WatchlistItem | None] = []
    for child in watchlist_rows:
        if child['is_empty']:
            watchlist.append(None)
            continue
        if child['ticker'] is None or child['region'] is None:
            raise ValueError(
                f'Account {row["email"]!r} has an invalid watchlist row',
            )
        watchlist.append(
            WatchlistItem(
                ticker=str(child['ticker']),
                region=str(child['region']),
                mode=str(child['rendering_mode']),
                llm_explanation=bool(child['llm_explanation']),
            )
        )

    portfolio_groups: dict[tuple[int, int], Stock] = {}
    for action_row in action_rows:
        group_key: tuple[int, int] = (
            int(action_row['ticker_id']),
            int(action_row['currency_id']),
        )
        if group_key not in portfolio_groups:
            portfolio_groups[group_key] = Stock(
                ticker=str(action_row['ticker']),
                region=str(action_row['region']),
                currency=str(action_row['currency']),
                actions=[],
            )
        portfolio_groups[group_key].actions.append(
            Action(
                action=str(action_row['action']),
                price=float(action_row['price']),
                quantity=int(action_row['quantity']),
                date=str(action_row['timestamp']),
            )
        )

    return Account(
        id=UUID(str(row['account_id'])),
        name=str(row['name']),
        email=str(row['email']),
        account_id=UUID(str(row['account_id'])),
        role=str(row['role']),
        language={
            'code': str(row['language_code']),
            'name': str(row['language_name']),
            'style': str(row['language_style']),
        },
        custom_report=custom_report,
        watchlist=watchlist,
        portfolio=list(portfolio_groups.values()),
    )


def _group_rows(
    rows: Iterable[LibSQLRow],
    key: str,
) -> dict[AccountId, list[LibSQLRow]]:
    grouped: defaultdict[AccountId, list[LibSQLRow]] = defaultdict(list)
    for row in rows:
        grouped[str(row[key])].append(row)
    return grouped


async def _load_accounts_from_connection(
    connection: AsyncDatabaseConnection,
    *,
    account_id: AccountId | None = None,
    email: str | None = None,
    name: str | None = None,
) -> list[Account]:
    query: str = f'''
        SELECT {_ACCOUNT_COLUMNS}
        FROM accounts
        JOIN languages ON languages.code = accounts.language_code
    '''
    parameters: tuple[str, ...] = ()
    if account_id is not None:
        query += ' WHERE accounts.account_id = ?'
        parameters = (account_id,)
    elif email is not None:
        query += ' WHERE accounts.email = ? COLLATE NOCASE'
        parameters = (email.strip(),)
    elif name is not None:
        query += ' WHERE accounts.name = ? COLLATE NOCASE'
        parameters = (name.strip(),)
    query += ' ORDER BY accounts.account_id'
    if account_id is not None or email is not None or name is not None:
        query += ' LIMIT 1'

    base_rows: list[LibSQLRow] = (
        await connection.execute(query, parameters)
    ).fetchall()
    if not base_rows:
        return []

    account_ids: list[AccountId] = [
        str(row['account_id'])
        for row in base_rows
    ]
    custom_rows, watchlist_rows, action_rows = await _load_related(
        connection,
        account_ids,
    )
    custom_by_account = _group_rows(custom_rows, 'account_id')
    watchlist_by_account = _group_rows(watchlist_rows, 'account_id')
    actions_by_account = _group_rows(action_rows, 'account_id')
    return [
        _account_from_parts(
            row,
            custom_by_account[str(row['account_id'])],
            watchlist_by_account[str(row['account_id'])],
            actions_by_account[str(row['account_id'])],
        )
        for row in base_rows
    ]


# ================================================== #
# ACCOUNT OPERATIONS                                 #
# ================================================== #

def _account_id_as_text(account_id: UUID | str) -> AccountId:
    if isinstance(account_id, UUID):
        return str(account_id)
    if not isinstance(account_id, str):
        raise TypeError('Account ID must be a UUID or UUID string')
    try:
        return str(UUID(account_id.strip()))
    except ValueError as e:
        raise ValueError(f'Invalid account UUID: {account_id!r}') from e


def _is_email_compatibility_value(value: UUID | str) -> bool:
    if not isinstance(value, str):
        return False
    try:
        UUID(value.strip())
    except ValueError:
        return '@' in value
    return False


async def load_accounts() -> list[Account]:
    await initialize_account_database()
    async with _connection() as connection:
        return await _load_accounts_from_connection(connection)


async def get_account(account_id: UUID | str) -> Account | None:
    """Load an account by UUID, with email routing for legacy callers."""

    # maybe this will disappear in future versions
    if _is_email_compatibility_value(account_id):
        return await get_account_by_email(str(account_id))
    return await get_account_by_id(account_id)


async def get_account_by_id(account_id: UUID | str) -> Account | None:
    """Load an account strictly by UUID."""

    account_id_text: AccountId = _account_id_as_text(account_id)
    await initialize_account_database()
    async with _connection() as connection:
        accounts: list[Account] = await _load_accounts_from_connection(
            connection,
            account_id=account_id_text,
        )
    return accounts[0] if accounts else None


async def get_account_by_email(email: str) -> Account | None:
    """Load an account by email."""

    await initialize_account_database()
    async with _connection() as connection:
        accounts: list[Account] = await _load_accounts_from_connection(
            connection,
            email=email,
        )
    return accounts[0] if accounts else None


async def _get_account_with_password_by_field(
    field_name: Literal['account_id', 'email', 'name'],
    value: str,
) -> tuple[Account | None, str | None]:
    lookup_value: str = (
        _account_id_as_text(value)
        if field_name == 'account_id'
        else value.strip()
    )
    await initialize_account_database()
    async with _connection() as connection:
        row: LibSQLRow | None = (
            await connection.execute(
                f'''
                SELECT {_ACCOUNT_COLUMNS}, accounts.password_hash
                FROM accounts
                JOIN languages ON languages.code = accounts.language_code
                WHERE accounts.{field_name} = ? COLLATE NOCASE
                LIMIT 1
                ''',
                (lookup_value,),
            )
        ).fetchone()
        if row is None:
            return None, None
        custom_rows, watchlist_rows, action_rows = await _load_related(
            connection,
            [str(row['account_id'])],
        )
    account: Account = _account_from_parts(
        row,
        custom_rows,
        watchlist_rows,
        action_rows,
    )
    return account, str(row['password_hash'])


async def get_account_with_password(
    account_id: UUID | str,
) -> tuple[Account | None, str | None]:
    """Load account credentials by UUID."""

    return await _get_account_with_password_by_field(
        'account_id',
        _account_id_as_text(account_id),
    )


async def get_account_with_password_by_email(
    email: str,
) -> tuple[Account | None, str | None]:
    """Load account credentials by email."""

    return await _get_account_with_password_by_field('email', email)


async def get_account_with_password_by_name(
    name: str,
) -> tuple[Account | None, str | None]:
    return await _get_account_with_password_by_field('name', name)


async def get_account_email_by_name(name: str) -> str | None:
    await initialize_account_database()
    async with _connection() as connection:
        row: LibSQLRow | None = (
            await connection.execute(
                '''
                SELECT email
                FROM accounts
                WHERE name = ? COLLATE NOCASE
                LIMIT 1
                ''',
                (name.strip(),),
            )
        ).fetchone()
    return str(row['email']) if row is not None else None


async def language_name(
    connection: AsyncDatabaseExecutor,
    language_code: str,
) -> str:
    row: LibSQLRow | None = (
        await connection.execute(
            'SELECT name FROM languages WHERE code = ? LIMIT 1',
            (language_code,),
        )
    ).fetchone()
    if row is None:
        raise ValueError(f'Language {language_code!r} does not exist')
    return str(row['name'])


async def create_account(account: Account, password_hash: str) -> Account:
    if not isinstance(password_hash, str) or not password_hash.strip():
        raise ValueError('A password is required to create an account')
    await initialize_account_database()
    pool = await _pool()
    try:
        async with pool.transaction() as connection:
            return await _insert_account(connection, account, password_hash)
    except DatabaseIntegrityError as e:
        raise AccountAlreadyExistsError(str(account.email)) from e


async def update_account(account: Account) -> Account | None:
    if account.account_id is None:
        raise ValueError('A UUID is required to update an account')
    account_id: AccountId = _account_id_as_text(account.account_id)
    await initialize_account_database()
    pool = await _pool()
    try:
        async with pool.transaction() as connection:
            row: LibSQLRow | None = (
                await connection.execute(
                    '''
                    SELECT account_id
                    FROM accounts
                    WHERE account_id = ?
                    LIMIT 1
                    ''',
                    (account_id,),
                )
            ).fetchone()
            if row is None:
                return None

            account_id = str(row['account_id'])
            await ensure_language(connection, account)
            await connection.execute(
                '''
                UPDATE accounts
                SET email = ?, name = ?, role = ?, language_code = ?, language_style = ?
                WHERE account_id = ?
                ''',
                (
                    str(account.email),
                    account.name,
                    account.role,
                    account.language.code,
                    account.language.style,
                    account_id,
                ),
            )
            await connection.execute(
                'DELETE FROM account_custom_reports WHERE account_id = ?',
                (account_id,),
            )
            await connection.execute(
                'DELETE FROM account_watchlist WHERE account_id = ?',
                (account_id,),
            )
            await connection.execute(
                'DELETE FROM action_history WHERE account_id = ?',
                (account_id,),
            )
            await insert_children(connection, account_id, account)
    except DatabaseIntegrityError as e:
        raise AccountAlreadyExistsError(str(account.email)) from e
    return account


async def delete_account(account_id: UUID | str) -> Account | None:
    """Delete an account by UUID, with email routing for legacy callers."""

    if _is_email_compatibility_value(account_id):
        return await delete_account_by_email(str(account_id))
    account: Account | None = await get_account_by_id(account_id)
    if account is None:
        return None
    return await _delete_account_record(account)


async def delete_account_by_email(email: str) -> Account | None:
    """Delete an account by email."""

    account: Account | None = await get_account_by_email(email)
    if account is None:
        return None
    return await _delete_account_record(account)


async def _delete_account_record(account: Account) -> Account:
    if account.account_id is None:
        raise RuntimeError(
            'A persisted account must have a UUID before deletion'
        )
    account_id: AccountId = _account_id_as_text(account.account_id)
    pool = await _pool()
    async with pool.transaction() as connection:
        await connection.execute(
            'DELETE FROM accounts WHERE account_id = ?',
            (account_id,),
        )
    return account


async def get_password_hash(account_id: UUID | str) -> str | None:
    """Return the stored password hash for an account UUID."""

    account_id_text: AccountId = _account_id_as_text(account_id)
    await initialize_account_database()
    async with _connection() as connection:
        row: LibSQLRow | None = (
            await connection.execute(
                '''
                SELECT password_hash
                FROM accounts
                WHERE account_id = ?
                LIMIT 1
                ''',
                (account_id_text,),
            )
        ).fetchone()
    if row is None or not row['password_hash']:
        return None
    return str(row['password_hash'])


async def update_password_hash(
    account_id: UUID | str,
    password_hash: str,
) -> bool:
    """Replace an account password hash and report whether the account exists."""

    if not isinstance(password_hash, str) or not password_hash.strip():
        raise ValueError('A password hash is required')
    account_id_text: AccountId = _account_id_as_text(account_id)
    await initialize_account_database()
    pool = await _pool()
    async with pool.transaction() as connection:
        result = await connection.execute(
            '''
            UPDATE accounts
            SET password_hash = ?
            WHERE account_id = ?
            ''',
            (password_hash, account_id_text),
        )
    return result.rowcount > 0


async def get_password_hash_by_email(email: str) -> str | None:
    """Return the stored password hash for an account email."""

    await initialize_account_database()
    async with _connection() as connection:
        row: LibSQLRow | None = (
            await connection.execute(
                '''
                SELECT password_hash
                FROM accounts
                WHERE email = ? COLLATE NOCASE
                LIMIT 1
                ''',
                (email.strip(),),
            )
        ).fetchone()
    if row is None or not row['password_hash']:
        return None
    return str(row['password_hash'])


async def import_accounts(
    accounts: Iterable[Account],
    password_hash: str,
) -> int:
    """Insert accounts supplied by the explicit data migration command."""

    if not isinstance(password_hash, str) or not password_hash.strip():
        raise ValueError('A password is required to import accounts')
    await initialize_account_database()
    imported: int = 0
    for account in accounts:
        if await get_account_by_email(str(account.email)) is not None:
            continue
        await create_account(account, password_hash)
        imported += 1
    return imported


__all__: list[str] = [
    'DATABASE_PATH',
    'create_account',
    'create_account_schema',
    'delete_account',
    'delete_account_by_email',
    'get_account',
    'get_account_by_email',
    'get_account_by_id',
    'get_account_email_by_name',
    'get_account_with_password',
    'get_account_with_password_by_email',
    'get_account_with_password_by_name',
    'get_password_hash',
    'get_password_hash_by_email',
    'import_accounts',
    'initialize_account_database',
    'insert_children',
    'insert_portfolio',
    'language_name',
    'load_accounts',
    'migrate_account_schema',
    'reset_account_schema',
    'update_account',
    'update_password_hash',
]
