"""Async normalized Turso/libSQL persistence for application accounts."""

import asyncio, json, logging
from pathlib import Path
from threading import RLock
from collections import defaultdict
from collections.abc import AsyncGenerator, Iterable, Sequence
from contextlib import asynccontextmanager
from typing import Any, Literal
from uuid import UUID, uuid4

from finance.config import (
    DB_AUTH_TOKEN,
    DB_LOCAL_PATH,
    DB_LOCATION,
    DB_POOL_SIZE,
    DB_POOL_TIMEOUT
)
from finance.services.account.exceptions import (
    AccountAlreadyExistsError,
    AccountSchemaException
)
from finance.services.account.models import Account, Action, Stock, WatchlistItem
from finance.services.account.vault import vault_sessions
from finance.services.database import (
    AsyncDatabaseConnection,
    DatabaseIntegrityError,
    DatabaseSyncError,
    LibSQLRow,
    get_database_pool,
    get_turso_sync_pool
)
from finance.services.database.repository import (
    AsyncDatabaseExecutor,
    create_schema,
    ensure_language,
    get_or_create_currency,
    get_or_create_ticker
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
    'technical'
)
_REPORT_MODES: tuple[str, ...] = (
    'classic',
    'full',
    'custom',
    'growth',
    'validation',
    'info'
)
type AccountId = str
_ACCOUNT_CHILD_TABLES: tuple[str, ...] = (
    'action_history',
    'account_custom_reports',
    'account_watchlist',
    'account_llm_api_keys'
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
        'custom_report_json',
    ),
    'account_watchlist': (
        'account_id',
        'position',
        'is_empty',
        'ticker_id',
        'rendering_mode',
        'llm_explanation',
    ),
    'account_llm_api_keys': (
        'account_id',
        'provider',
        'encrypted_value',
    ),
}
_LEGACY_ACCOUNT_CHILD_COLUMNS: dict[str, tuple[str, ...]] = {
    'action_history': _ACCOUNT_CHILD_COLUMNS['action_history'],
    'account_custom_reports': (
        'account_id',
        'position',
        'metric',
    ),
    'account_watchlist': _ACCOUNT_CHILD_COLUMNS['account_watchlist'],
}
_schema_ready: set[str] = set()
_schema_locks: dict[str, asyncio.Lock] = {}
_schema_registry_lock: RLock = RLock()


# ================================================== #
# HELPER FUNCTIONS                                   #
# ================================================== # 

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
async def _connection() -> AsyncGenerator[AsyncDatabaseConnection, None]:
    pool = await _pool()
    async with pool.connection() as connection:
        yield connection



# ================================================== #
# SCHEMA                                             #
# ================================================== #

async def _table_exists(conn: AsyncDatabaseExecutor, table_name: str) -> bool:
    row: LibSQLRow | None = (
        await conn.execute(
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


async def _table_columns(conn: AsyncDatabaseExecutor, table_name: str) -> dict[str, LibSQLRow]:
    return {
        str(row['name']): row
        for row in (
            await conn.execute(
                f'PRAGMA table_info({table_name})',
            )
        ).fetchall()
    }


async def _account_schema_is_current(conn: AsyncDatabaseExecutor) -> bool:
    if not await _table_exists(conn, 'accounts'):
        return False

    columns: dict[str, LibSQLRow] = await _table_columns(
        conn,
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
        'encrypted_umk',
    }
    if not required_columns.issubset(columns):
        return False

    account_id_column: LibSQLRow = columns['account_id']
    role_column: LibSQLRow = columns['role']
    encrypted_umk_column: LibSQLRow = columns['encrypted_umk']
    if (
        str(account_id_column['type']).upper() != 'TEXT'
        or int(account_id_column['notnull']) != 1
        or int(account_id_column['pk']) != 1
        or str(role_column['type']).upper() != 'TEXT'
        or int(role_column['notnull']) != 1
        or str(encrypted_umk_column['type']).upper() != 'TEXT'
    ):
        return False

    for table_name in _ACCOUNT_CHILD_TABLES:
        if not await _table_exists(conn, table_name):
            return False
        
        child_columns: dict[str, LibSQLRow] = await _table_columns(
            conn,
            table_name,
        )

        if set(child_columns) != set(_ACCOUNT_CHILD_COLUMNS[table_name]):
            return False
        
        account_id_column = child_columns.get('account_id')
        if (
            account_id_column is None
            or str(account_id_column['type']).upper() != 'TEXT'
            or int(account_id_column['notnull']) != 1
        ):
            return False
        
        if table_name == 'account_custom_reports':
            report_json_column: LibSQLRow = child_columns[ 'custom_report_json' ]
            if (
                str(report_json_column['type']).upper() != 'TEXT'
                or int(report_json_column['notnull']) != 1
                or int(report_json_column['pk']) != 0
                or int(account_id_column['pk']) != 1
            ):
                return False
        
        if table_name == 'account_llm_api_keys':
            provider_column: LibSQLRow = child_columns['provider']
            encrypted_value_column: LibSQLRow = child_columns[ 'encrypted_value' ]
            if (
                str(provider_column['type']).upper() != 'TEXT'
                or int(provider_column['notnull']) != 1
                or int(provider_column['pk']) != 2
                or int(account_id_column['pk']) != 1
                or str(encrypted_value_column['type']).upper() != 'TEXT'
                or int(encrypted_value_column['notnull']) != 1
            ):
                return False

    missing_custom_report: LibSQLRow | None = (
        await conn.execute(
            '''
            SELECT accounts.account_id
            FROM accounts
            LEFT JOIN account_custom_reports
                ON account_custom_reports.account_id = accounts.account_id
            WHERE account_custom_reports.account_id IS NULL
            LIMIT 1
            ''',
        )
    ).fetchone()
    return missing_custom_report is None


async def _create_account_tables(conn: AsyncDatabaseExecutor, table_suffix: str = '') -> None:
    accounts_table: str = f'accounts{table_suffix}'
    action_history_table: str = f'action_history{table_suffix}'
    custom_reports_table: str = f'account_custom_reports{table_suffix}'
    watchlist_table: str = f'account_watchlist{table_suffix}'

    await conn.execute(
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
            password_hash TEXT NOT NULL,
            encrypted_umk TEXT
        )
        '''
    )
    await conn.execute(
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
    await conn.execute(
        f'''
        CREATE TABLE IF NOT EXISTS {custom_reports_table} (
            account_id TEXT NOT NULL PRIMARY KEY
                REFERENCES {accounts_table}(account_id) ON DELETE CASCADE,
            custom_report_json TEXT NOT NULL
        )
        '''
    )
    await conn.execute(
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
    await conn.execute(
        f'''
        CREATE TABLE IF NOT EXISTS account_llm_api_keys{table_suffix} (
            account_id TEXT NOT NULL
                REFERENCES {accounts_table}(account_id) ON DELETE CASCADE,
            provider TEXT NOT NULL
                CHECK (provider IN ('deepseek', 'anthropic', 'chatgpt')),
            encrypted_value TEXT NOT NULL,
            PRIMARY KEY (account_id, provider)
        )
        '''
    )


async def create_account_schema(conn: AsyncDatabaseExecutor) -> None:
    await _create_account_tables(conn)
    await conn.execute(
        '''
        CREATE INDEX IF NOT EXISTS idx_accounts_name_nocase
        ON accounts(name COLLATE NOCASE)
        '''
    )
    await conn.execute(
        '''
        CREATE INDEX IF NOT EXISTS idx_action_history_account_action
        ON action_history(account_id, action_id)
        '''
    )


async def _validate_legacy_account_schema(conn: AsyncDatabaseExecutor) -> dict[str, LibSQLRow]:
    account_columns: dict[str, LibSQLRow] = await _table_columns(conn, 'accounts')
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
        raise AccountSchemaException('The legacy role column must use TEXT; no data was changed.')

    for table_name, expected_columns in _LEGACY_ACCOUNT_CHILD_COLUMNS.items():
        if not await _table_exists(conn, table_name):
            continue
        child_columns: dict[str, LibSQLRow] = await _table_columns(conn, table_name,)

        if set(child_columns) != set(expected_columns):
            raise AccountSchemaException(
                f'The account migration does not recognize table '
                f'{table_name!r}; no data was changed.'
            )
        
        account_id_column = child_columns['account_id']
        if str(account_id_column['type']).upper() != 'INTEGER':
            raise AccountSchemaException(f'Table {table_name!r} does not use integer account IDs; no data was changed.')

    if await _table_exists(conn, 'account_llm_api_keys'):
        key_columns: dict[str, LibSQLRow] = await _table_columns(conn, 'account_llm_api_keys',)

        if set(key_columns) != set(_ACCOUNT_CHILD_COLUMNS['account_llm_api_keys']):
            raise AccountSchemaException(
                'The integer-ID migration does not recognize '
                'account_llm_api_keys; no data was changed.'
            )
        
        if await _table_row_count(conn, 'account_llm_api_keys'):
            raise AccountSchemaException(
                'Encrypted LLM keys cannot be rebound from integer IDs to '
                'UUIDs; export or remove them before this migration.'
            )

    return account_columns


async def _table_row_count(conn: AsyncDatabaseExecutor, table_name: str) -> int:
    row: LibSQLRow | None = (
        await conn.execute(
            f'SELECT COUNT(*) AS row_count FROM {table_name}',
        )
    ).fetchone()

    if row is None:
        raise RuntimeError(f'Could not count rows in table {table_name!r}')
    return int(row['row_count'])


async def _assert_account_foreign_keys(conn: AsyncDatabaseExecutor, table_names: Sequence[str]) -> None:
    for table_name in table_names:
        violations: list[LibSQLRow] = (
            await conn.execute(
                f'PRAGMA foreign_key_check({table_name})',
            )
        ).fetchall()

        if violations:
            raise AccountSchemaException(
                f'Foreign-key validation failed for {table_name!r}: '
                f'{violations[0]!r}.'
            )

# this function below was generated by a LLM, and it length is significant.
async def _migrate_integer_account_schema(conn: AsyncDatabaseExecutor) -> None:
    account_columns: dict[str, LibSQLRow] = await _validate_legacy_account_schema(conn)
    staged_tables: tuple[str, ...] = (
        f'accounts{_ACCOUNT_MIGRATION_SUFFIX}',
        *(
            f'{table_name}{_ACCOUNT_MIGRATION_SUFFIX}'
            for table_name in _ACCOUNT_CHILD_TABLES
        ),
    )

    for table_name in (*staged_tables, _ACCOUNT_ID_MAP_TABLE):
        if await _table_exists(conn, table_name):
            raise AccountSchemaException(
                f'An account migration staging table {table_name!r} already '
                'exists; inspect the database before retrying.'
            )

    await conn.execute(
        f'''
        CREATE TABLE {_ACCOUNT_ID_MAP_TABLE} (
            old_account_id INTEGER PRIMARY KEY,
            new_account_id TEXT NOT NULL UNIQUE
        )
        '''
    )

    old_account_rows: list[LibSQLRow] = (
        await conn.execute('SELECT account_id FROM accounts ORDER BY account_id')
    ).fetchall()
    for row in old_account_rows:
        await conn.execute(
            f'''
            INSERT INTO {_ACCOUNT_ID_MAP_TABLE} (
                old_account_id, new_account_id
            )
            VALUES (?, ?)
            ''',
            (int(row['account_id']), str(uuid4())),
        )

    await _create_account_tables(conn,_ACCOUNT_MIGRATION_SUFFIX,)
    role_expression: str = (
        "COALESCE(source.role, 'user')"
        if 'role' in account_columns
        else "'user'"
    )
    await conn.execute(
        f'''
        INSERT INTO accounts{_ACCOUNT_MIGRATION_SUFFIX} (
            account_id, email, name, role, language_code,
            language_style, password_hash, encrypted_umk
        )
        SELECT id_map.new_account_id, source.email, source.name,
               {role_expression}, source.language_code,
               source.language_style, source.password_hash, NULL
        FROM accounts AS source
        JOIN {_ACCOUNT_ID_MAP_TABLE} AS id_map
          ON id_map.old_account_id = source.account_id
        '''
    )

    for table_name in ('action_history', 'account_watchlist'):
        if not await _table_exists(conn, table_name):
            continue
        columns: tuple[str, ...] = _ACCOUNT_CHILD_COLUMNS[table_name]
        column_list: str = ', '.join(columns)
        selected_columns: str = ', '.join(
            (
                'id_map.new_account_id'
                if column == 'account_id'
                else f'source.{column}'
            )
            for column in columns
        )

        await conn.execute(
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

    legacy_report_rows: dict[int, list[str]] = defaultdict(list)
    if await _table_exists(conn, 'account_custom_reports'):
        report_rows: list[LibSQLRow] = (
            await conn.execute(
                '''
                SELECT account_id, position, metric
                FROM account_custom_reports
                ORDER BY account_id, position
                ''',
            )
        ).fetchall()
        for row in report_rows:
              metric: object = row['metric']
              if not isinstance(metric, str):
                  raise AccountSchemaException(
                      'A legacy custom report metric is not text; '
                      'no data was changed.'
                  )
              legacy_report_rows[int(row['account_id'])].append(metric)

    id_map_rows: list[LibSQLRow] = (
        await conn.execute(
              f'''
              SELECT old_account_id, new_account_id
              FROM {_ACCOUNT_ID_MAP_TABLE}
              ORDER BY old_account_id
              ''',
        )
    ).fetchall()
    mapped_old_ids: set[int] = {
        int(row['old_account_id'])
        for row in id_map_rows
    }

    if not set(legacy_report_rows).issubset(mapped_old_ids):
        raise AccountSchemaException('A legacy custom report references an unknown account; no data was changed.')
    for row in id_map_rows:
        old_account_id: int = int(row['old_account_id'])
        custom_report_json: str = json.dumps(
            legacy_report_rows.get(old_account_id, []),
            ensure_ascii=False,
            separators=(',', ':'),
        )
        await conn.execute(
            f'''
            INSERT INTO account_custom_reports{_ACCOUNT_MIGRATION_SUFFIX} (
                account_id, custom_report_json
            )
            VALUES (?, ?)
            ''',
            (str(row['new_account_id']), custom_report_json),
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
        if not await _table_exists(conn, source_table):
            continue

        source_count: int = await _table_row_count(
            conn,
            source_table,
        )
        staged_count: int = await _table_row_count(
            conn,
            staged_table,
        )
        expected_staged_count: int = source_count
        if source_table == 'account_custom_reports':
            expected_staged_count = len(id_map_rows)
        if staged_count != expected_staged_count:
            raise AccountSchemaException(
                f'Account migration row count mismatch for '
                f'{source_table!r}; no source tables were replaced.'
            )

    await _assert_account_foreign_keys(conn, staged_tables)

    for table_name in _ACCOUNT_CHILD_TABLES:
        if await _table_exists(conn, table_name):
            await conn.execute(f'DROP TABLE {table_name}')
    await conn.execute('DROP TABLE accounts')
    await conn.execute(
        f'''
        ALTER TABLE accounts{_ACCOUNT_MIGRATION_SUFFIX}
        RENAME TO accounts
        '''
    )
    for table_name in _ACCOUNT_CHILD_TABLES:
        await conn.execute(
            f'''
            ALTER TABLE {table_name}{_ACCOUNT_MIGRATION_SUFFIX}
            RENAME TO {table_name}
            '''
        )
    await conn.execute(f'DROP TABLE {_ACCOUNT_ID_MAP_TABLE}')
    await create_account_schema(conn)
    await _assert_account_foreign_keys(
        conn,
        ('accounts', *_ACCOUNT_CHILD_TABLES),
    )


async def _migrate_uuid_account_schema(conn: AsyncDatabaseExecutor) -> None:
    account_columns: dict[str, LibSQLRow] = await _table_columns(conn, 'accounts')
    account_id_column: LibSQLRow | None = account_columns.get('account_id')
    required_account_columns: set[str] = {
        'account_id',
        'email',
        'name',
        'role',
        'language_code',
        'language_style',
        'password_hash',
    }
    if (
        not required_account_columns.issubset(account_columns)
        or account_id_column is None
        or str(account_id_column['type']).upper() != 'TEXT'
        or int(account_id_column['pk']) != 1
    ):
        raise AccountSchemaException(
            'The UUID account schema is not recognized; no data was changed.'
        )
    
    if 'encrypted_umk' not in account_columns:
        await conn.execute(
            'ALTER TABLE accounts ADD COLUMN encrypted_umk TEXT',
        )

    if await _table_exists(conn, 'account_custom_reports'):
        report_columns: dict[str, LibSQLRow] = await _table_columns(conn, 'account_custom_reports')
        column_names: set[str] = set(report_columns)
        legacy_columns: set[str] = set(
            _LEGACY_ACCOUNT_CHILD_COLUMNS['account_custom_reports'],
        )
        current_columns: set[str] = set(
            _ACCOUNT_CHILD_COLUMNS['account_custom_reports'],
        )
        if column_names == legacy_columns:
            staging_table: str = 'account_custom_reports_uuid_migration'
            if await _table_exists(conn, staging_table):
                raise AccountSchemaException(
                    f'An account migration staging table {staging_table!r} '
                    'already exists; inspect the database before retrying.'
                )
            
            await conn.execute(
                f'''
                CREATE TABLE {staging_table} (
                    account_id TEXT NOT NULL PRIMARY KEY
                        REFERENCES accounts(account_id) ON DELETE CASCADE,
                    custom_report_json TEXT NOT NULL
                )
                '''
            )

            account_rows: list[LibSQLRow] = (
                await conn.execute(
                    'SELECT account_id FROM accounts ORDER BY account_id',
                )
            ).fetchall()
            legacy_rows: list[LibSQLRow] = (
                await conn.execute(
                    '''
                    SELECT account_id, position, metric
                    FROM account_custom_reports
                    ORDER BY account_id, position
                    ''',
                )
            ).fetchall()
            
            reports_by_account: defaultdict[str, list[str]] = defaultdict(list)
            for row in legacy_rows:
                metric: object = row['metric']
                if not isinstance(metric, str):
                    raise AccountSchemaException(
                        'A legacy custom report metric is not text; no data was changed.'
                    )
                reports_by_account[str(row['account_id'])].append(metric)

            account_ids: set[str] = {
                str(row['account_id'])
                for row in account_rows
            }
            if not set(reports_by_account).issubset(account_ids):
                raise AccountSchemaException(
                    'A legacy custom report references an unknown account; no data was changed.'
                )
            for row in account_rows:
                account_id: str = str(row['account_id'])
                custom_report_json = json.dumps(
                    reports_by_account.get(account_id, []),
                    ensure_ascii=False,
                    separators=(',', ':'),
                )
                await conn.execute(
                    f'''
                    INSERT INTO {staging_table} (
                        account_id, custom_report_json
                    )
                    VALUES (?, ?)
                    ''',
                    (account_id, custom_report_json),
                )

            await conn.execute('DROP TABLE account_custom_reports')
            await conn.execute(
                f'''
                ALTER TABLE {staging_table}
                RENAME TO account_custom_reports
                '''
            )
        
        elif column_names != current_columns:
            raise AccountSchemaException(
                'The account_custom_reports schema is not recognized; '
                'no data was changed.'
            )

    await _create_account_tables(conn)
    await conn.execute(
        '''
        INSERT INTO account_custom_reports (
            account_id, custom_report_json
        )
        SELECT accounts.account_id, '[]'
        FROM accounts
        LEFT JOIN account_custom_reports
            ON account_custom_reports.account_id = accounts.account_id
        WHERE account_custom_reports.account_id IS NULL
        '''
    )
    await create_account_schema(conn)
    await _assert_account_foreign_keys(
        conn,
        ('accounts', *_ACCOUNT_CHILD_TABLES),
    )


async def migrate_account_schema() -> bool:
    """Migrate supported account schemas without losing their relationships."""

    key: str = _database_key()
    pool = await _pool()
    if pool.is_turso_sync:
        raise AccountSchemaException(
            'Account schema changes must be applied through the approved '
            'Turso schema migration, not the runtime sync token.'
        )
    
    migrated: bool = False
    async with pool.transaction() as conn:
        if not await _table_exists(conn, 'accounts'):
            return False
        
        if await _account_schema_is_current(conn):
            return False
        
        account_columns: dict[str, LibSQLRow] = await _table_columns(conn, 'accounts')
        account_id_column: LibSQLRow | None = account_columns.get('account_id')
        account_id_type: str = (
            str(account_id_column['type']).upper()
            if account_id_column is not None
            else ''
        )

        if account_id_type == 'INTEGER':
            await _migrate_integer_account_schema(conn)
        elif account_id_type == 'TEXT':
            await _migrate_uuid_account_schema(conn)
        else:
            raise AccountSchemaException('The account schema is not recognized; no data was changed.')
        
        if not await _account_schema_is_current(conn):
            raise AccountSchemaException('The account migration did not produce the current schema.')
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
            base_tables: tuple[str, ...] = (
                'languages',
                'tickers',
                'currencies',
                'accounts',
                'action_history',
                'account_custom_reports',
                'account_watchlist',
            )
            async with pool.transaction() as connection:
                existing_tables: list[str] = [
                    table_name
                    for table_name in base_tables
                    if await _table_exists(connection, table_name)
                ]

                if not existing_tables:
                    await create_schema(connection)
                    await create_account_schema(connection)
                elif len(existing_tables) != len(base_tables):
                    missing_tables: list[str] = [
                        table_name
                        for table_name in base_tables
                        if table_name not in existing_tables
                    ]
                    raise AccountSchemaException(
                        'The local account database is incomplete; missing '
                        f'tables: {", ".join(missing_tables)}.'
                    )

            async with pool.connection() as connection:
                is_current_schema: bool = await _account_schema_is_current(connection)
            
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
        raise AccountSchemaException('Account tables cannot be reset in a Turso Sync database.')
    
    async with pool.transaction() as conn:
        for table_name in (
            'account_watchlist',
            'account_llm_api_keys',
            'account_custom_reports',
            'action_history',
            'accounts',
        ):
            await conn.execute(f'DROP TABLE IF EXISTS {table_name}')
        await create_schema(conn)
        await create_account_schema(conn)
    vault_sessions.clear()
    _schema_ready.add(key)


# ================================================== #
# WRITE HELPERS                                      #
# ================================================== #

async def insert_portfolio(
    conn: AsyncDatabaseExecutor,
    account_id: AccountId,
    account: Account
) -> None:
    action_values: list[tuple[Any, ...]] = []
    for stock in account.portfolio:
        if stock is None:
            continue

        ticker_id: int = await get_or_create_ticker(
            conn,
            stock.ticker,
            stock.region,
        )
        currency_id: int = await get_or_create_currency(
            conn,
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
    
    placeholders: str = ', '.join('(?, ?, ?, ?, ?, ?, ?)' for _ in action_values)
    flattened: tuple[Any, ...] = tuple(
        value
        for row in action_values
        for value in row
    )
    await conn.execute(
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
    conn: AsyncDatabaseExecutor,
    account_id: AccountId,
    account: Account
) -> None:
    custom_report_json: str = json.dumps(
        account.custom_report,
        ensure_ascii=False,
        separators=(',', ':'),
    )
    await conn.execute(
        '''
        INSERT INTO account_custom_reports (account_id, custom_report_json)
        VALUES (?, ?)
        ''',
        (account_id, custom_report_json),
    )

    watchlist_values: list[tuple[Any, ...]] = []
    for position, item in enumerate(account.watchlist):
        if item is None:
            watchlist_values.append((account_id, position, 1, None, None, 0))
            continue
        ticker_id: int = await get_or_create_ticker(
            conn,
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
        await conn.execute(
            f'''
            INSERT INTO account_watchlist (
                account_id, position, is_empty, ticker_id,
                rendering_mode, llm_explanation
            )
            VALUES {watchlist_placeholders}
            ''',
            tuple(value for row in watchlist_values for value in row),
        )

    await insert_portfolio(conn, account_id, account)


async def _insert_account(
    conn: AsyncDatabaseExecutor,
    account: Account,
    password_hash: str,
    encrypted_umk: str | None
) -> Account:
    await ensure_language(conn, account)
    account_uuid: UUID = account.account_id or account.id
    account_id: AccountId = str(account_uuid)
    await conn.execute(
        '''
        INSERT INTO accounts (
            account_id, email, name, role,
            language_code, language_style, password_hash, encrypted_umk
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            account_id,
            str(account.email),
            account.name,
            account.role,
            account.language.code,
            account.language.style,
            password_hash,
            encrypted_umk,
        ),
    )

    await insert_children(conn, account_id, account)
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
    conn: AsyncDatabaseConnection,
    account_ids: Sequence[AccountId]
) -> tuple[list[LibSQLRow], list[LibSQLRow], list[LibSQLRow]]:
    if not account_ids:
        return [], [], []
    
    placeholders: str = _placeholders(account_ids)
    custom_reports, watchlists, actions = await conn.batch(
        [
            (
                f'''
                SELECT account_id, custom_report_json
                FROM account_custom_reports
                WHERE account_id IN ({placeholders})
                ORDER BY account_id
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
    action_rows: Iterable[LibSQLRow]
) -> Account:
    custom_report_rows: list[LibSQLRow] = list(custom_rows)
    custom_report: list[str] = []
    if custom_report_rows:
        try:
            stored_custom_report: Any = json.loads(
                str(custom_report_rows[0]['custom_report_json']),
            )
        except json.JSONDecodeError as e:
            raise AccountSchemaException(f'Account {row["email"]!r} has invalid custom report JSON.') from e
        if (
            not isinstance(stored_custom_report, list)
            or not all(
                isinstance(metric, str)
                for metric in stored_custom_report
            )
        ):
            raise AccountSchemaException(f'Account {row["email"]!r} has invalid custom report data.')
        custom_report = stored_custom_report
    
    watchlist: list[WatchlistItem | None] = []
    for child in watchlist_rows:
        if child['is_empty']:
            watchlist.append(None)
            continue

        if child['ticker'] is None or child['region'] is None:
            raise ValueError(f'Account {row["email"]!r} has an invalid watchlist row')
        
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
    key: str
) -> dict[AccountId, list[LibSQLRow]]:
    grouped: defaultdict[AccountId, list[LibSQLRow]] = defaultdict(list)
    for row in rows:
        grouped[str(row[key])].append(row)
    return grouped


async def _load_accounts_from_connection(
    conn: AsyncDatabaseConnection,
    *,
    account_id: AccountId | None = None,
    email: str | None = None,
    name: str | None = None
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
        await conn.execute(query, parameters)
    ).fetchall()
    if not base_rows:
        return []

    account_ids: list[AccountId] = [
        str(row['account_id'])
        for row in base_rows
    ]
    custom_rows, watchlist_rows, action_rows = await _load_related(
        conn,
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
    value: str
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


async def get_account_with_password(account_id: UUID | str) -> tuple[Account | None, str | None]:
    """Load account credentials by UUID."""

    return await _get_account_with_password_by_field(
        'account_id',
        _account_id_as_text(account_id),
    )


async def get_account_with_password_by_email(email: str) -> tuple[Account | None, str | None]:
    """Load account credentials by email."""
    return await _get_account_with_password_by_field('email', email)


async def get_account_with_password_by_name(name: str) -> tuple[Account | None, str | None]:
    return await _get_account_with_password_by_field('name', name)


async def get_account_email_by_name(name: str) -> str | None:
    await initialize_account_database()
    async with _connection() as conn:
        row: LibSQLRow | None = (
            await conn.execute(
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


async def language_name(conn: AsyncDatabaseExecutor, language_code: str) -> str:
    row: LibSQLRow | None = (
        await conn.execute(
            'SELECT name FROM languages WHERE code = ? LIMIT 1',
            (language_code,),
        )
    ).fetchone()
    if row is None:
        raise ValueError(f'Language {language_code!r} does not exist')
    return str(row['name'])


async def create_account(
    account: Account,
    password_hash: str,
    encrypted_umk: str | None = None
) -> Account:
    if not isinstance(password_hash, str) or not password_hash.strip():
        raise ValueError('A password is required to create an account')
    await initialize_account_database()
    
    pool = await _pool()
    try:
        async with pool.transaction() as connection:
            return await _insert_account(
                connection,
                account,
                password_hash,
                encrypted_umk,
            )
    
    except DatabaseIntegrityError as e:
        raise AccountAlreadyExistsError(str(account.email)) from e


async def get_account_umk_envelope(account_id: UUID | str) -> str | None:
    account_id_text: AccountId = _account_id_as_text(account_id)
    await initialize_account_database()
    async with _connection() as connection:
        row: LibSQLRow | None = (
            await connection.execute(
                '''
                SELECT encrypted_umk
                FROM accounts
                WHERE account_id = ?
                LIMIT 1
                ''',
                (account_id_text,),
            )
        ).fetchone()

    if row is None or row['encrypted_umk'] is None:
        return None
    return str(row['encrypted_umk'])


async def set_account_umk_envelope_if_missing(
    account_id: UUID | str,
    envelope: str
) -> bool:
    if not isinstance(envelope, str) or not envelope.strip():
        raise ValueError('An encrypted UMK envelope is required.')
    
    account_id_text: AccountId = _account_id_as_text(account_id)
    await initialize_account_database()
    pool = await _pool()
    async with pool.transaction() as connection:
        result = await connection.execute(
            '''
            UPDATE accounts
            SET encrypted_umk = ?
            WHERE account_id = ? AND encrypted_umk IS NULL
            ''',
            (envelope, account_id_text),
        )
    return result.rowcount == 1


async def load_account_llm_key_envelopes(account_id: UUID | str) -> dict[str, str]:
    account_id_text: AccountId = _account_id_as_text(account_id)
    await initialize_account_database()
    async with _connection() as connection:
        rows: list[LibSQLRow] = (
            await connection.execute(
                '''
                SELECT provider, encrypted_value
                FROM account_llm_api_keys
                WHERE account_id = ?
                ORDER BY provider
                ''',
                (account_id_text,),
            )
        ).fetchall()

    return {
        str(row['provider']): str(row['encrypted_value'])
        for row in rows
    }


async def upsert_account_llm_key_envelope(
    account_id: UUID | str,
    provider: str,
    envelope: str
) -> None:
    if provider not in {'deepseek', 'anthropic', 'chatgpt'}:
        raise ValueError(f'Unsupported LLM provider: {provider!r}.')
    if not isinstance(envelope, str) or not envelope.strip():
        raise ValueError('An encrypted provider key envelope is required.')
    
    account_id_text: AccountId = _account_id_as_text(account_id)
    await initialize_account_database()
    pool = await _pool()
    async with pool.transaction() as connection:
        await connection.execute(
            '''
            INSERT INTO account_llm_api_keys (
                account_id, provider, encrypted_value
            )
            VALUES (?, ?, ?)
            ON CONFLICT(account_id, provider)
            DO UPDATE SET encrypted_value = excluded.encrypted_value
            ''',
            (account_id_text, provider, envelope),
        )


async def delete_account_llm_key(account_id: UUID | str, provider: str) -> bool:
    if provider not in {'deepseek', 'anthropic', 'chatgpt'}:
        raise ValueError(f'Unsupported LLM provider: {provider!r}.')
    
    account_id_text: AccountId = _account_id_as_text(account_id)
    await initialize_account_database()
    pool = await _pool()
    async with pool.transaction() as connection:
        result = await connection.execute(
            '''
            DELETE FROM account_llm_api_keys
            WHERE account_id = ? AND provider = ?
            ''',
            (account_id_text, provider),
        )
    return result.rowcount > 0


async def update_account_password_and_umk(
    account_id: UUID | str,
    password_hash: str,
    encrypted_umk: str
) -> bool:
    if not isinstance(password_hash, str) or not password_hash.strip():
        raise ValueError('A password hash is required.')
    if not isinstance(encrypted_umk, str) or not encrypted_umk.strip():
        raise ValueError('An encrypted UMK envelope is required.')
    
    account_id_text: AccountId = _account_id_as_text(account_id)
    await initialize_account_database()
    pool = await _pool()
    async with pool.transaction() as connection:
        result = await connection.execute(
            '''
            UPDATE accounts
            SET password_hash = ?, encrypted_umk = ?
            WHERE account_id = ?
            ''',
            (password_hash, encrypted_umk, account_id_text),
        )
    return result.rowcount > 0


async def replace_account_umk_and_clear_llm_keys(
    account_id: UUID | str,
    encrypted_umk: str
) -> bool:
    if not isinstance(encrypted_umk, str) or not encrypted_umk.strip():
        raise ValueError('An encrypted UMK envelope is required.')
    
    account_id_text: AccountId = _account_id_as_text(account_id)
    await initialize_account_database()
    pool = await _pool()
    async with pool.transaction() as connection:
        updated = await connection.execute(
            '''
            UPDATE accounts
            SET encrypted_umk = ?
            WHERE account_id = ?
            ''',
            (encrypted_umk, account_id_text),
        )

        if updated.rowcount == 0:
            return False
        await connection.execute(
            'DELETE FROM account_llm_api_keys WHERE account_id = ?',
            (account_id_text,),
        )
    return True


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
        raise RuntimeError('A persisted account must have a UUID before deletion')
    
    account_id: AccountId = _account_id_as_text(account.account_id)
    pool = await _pool()
    async with pool.transaction() as connection:
        await connection.execute(
            'DELETE FROM accounts WHERE account_id = ?',
            (account_id,),
        )
    vault_sessions.lock(account_id)
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


async def get_password_hash_by_email(email: str) -> str | None:
    """Return the stored password hash for an account email."""

    await initialize_account_database()
    async with _connection() as conn:
        row: LibSQLRow | None = (
            await conn.execute(
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


async def import_accounts(accounts: Iterable[Account], password_hash: str) -> int:
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
