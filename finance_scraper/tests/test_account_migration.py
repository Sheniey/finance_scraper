import tempfile
import unittest
from pathlib import Path
from uuid import UUID

from finance.config import DB_AUTH_TOKEN, DB_POOL_SIZE, DB_POOL_TIMEOUT
from finance.services.account import db as account_storage
from finance.services.account.exceptions import AccountSchemaException
from finance.services.database import close_database_pools, get_database_pool
from finance.services.database.repository import (
    AsyncDatabaseExecutor,
    create_schema,
)


async def _create_legacy_schema(
    connection: AsyncDatabaseExecutor,
    *,
    extra_account_column: bool = False,
) -> None:
    await create_schema(connection)
    extra_column: str = ', unexpected TEXT' if extra_account_column else ''
    await connection.execute(
        f'''
        CREATE TABLE accounts (
            account_id INTEGER PRIMARY KEY,
            email TEXT NOT NULL COLLATE NOCASE UNIQUE,
            name TEXT NOT NULL,
            language_code TEXT NOT NULL REFERENCES languages(code),
            language_style TEXT NOT NULL
                CHECK (language_style IN (
                    'friendly', 'professional', 'technical'
                )),
            password_hash TEXT NOT NULL
            {extra_column}
        )
        '''
    )
    await connection.execute(
        '''
        CREATE TABLE action_history (
            action_id INTEGER PRIMARY KEY,
            account_id INTEGER NOT NULL
                REFERENCES accounts(account_id) ON DELETE CASCADE,
            ticker_id INTEGER NOT NULL REFERENCES tickers(ticker_id),
            currency_id INTEGER NOT NULL REFERENCES currencies(currency_id),
            action TEXT NOT NULL CHECK (action IN ('BUY', 'SELL')),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            price REAL NOT NULL CHECK (price >= 0),
            timestamp DATETIME NOT NULL
        )
        '''
    )
    await connection.execute(
        '''
        CREATE TABLE account_custom_reports (
            account_id INTEGER NOT NULL
                REFERENCES accounts(account_id) ON DELETE CASCADE,
            position INTEGER NOT NULL,
            metric TEXT NOT NULL,
            PRIMARY KEY (account_id, position)
        )
        '''
    )
    await connection.execute(
        '''
        CREATE TABLE account_watchlist (
            account_id INTEGER NOT NULL
                REFERENCES accounts(account_id) ON DELETE CASCADE,
            position INTEGER NOT NULL CHECK (position >= 0),
            is_empty INTEGER NOT NULL DEFAULT 0
                CHECK (is_empty IN (0, 1)),
            ticker_id INTEGER REFERENCES tickers(ticker_id),
            rendering_mode TEXT NOT NULL DEFAULT 'classic'
                CHECK (rendering_mode IN (
                    'classic', 'full', 'custom',
                    'growth', 'validation', 'info'
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


class AccountSchemaMigrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._original_pool_factory = account_storage._pool

        async def get_local_test_pool():
            return await get_database_pool(
                account_storage.DATABASE_PATH,
                auth_token=DB_AUTH_TOKEN,
                size=DB_POOL_SIZE,
                acquire_timeout=DB_POOL_TIMEOUT,
            )

        account_storage._pool = get_local_test_pool

    async def asyncTearDown(self) -> None:
        account_storage._pool = self._original_pool_factory
        await close_database_pools()

    async def test_integer_account_ids_migrate_and_preserve_relationships(
        self,
    ) -> None:
        original_account_path: str | Path = account_storage.DATABASE_PATH

        with tempfile.TemporaryDirectory() as directory:
            database_path: Path = Path(directory) / 'legacy_accounts.sqlite3'
            account_storage.DATABASE_PATH = database_path
            try:
                pool = await get_database_pool(
                    database_path,
                    auth_token=DB_AUTH_TOKEN,
                    size=DB_POOL_SIZE,
                    acquire_timeout=DB_POOL_TIMEOUT,
                )
                async with pool.transaction() as connection:
                    await _create_legacy_schema(connection)
                    await connection.execute(
                        'INSERT INTO languages (code, name) VALUES (?, ?)',
                        ('en', 'English'),
                    )
                    await connection.execute(
                        '''
                        INSERT INTO tickers (ticker_id, ticker, region)
                        VALUES (?, ?, ?)
                        ''',
                        (1, 'AAPL', 'US'),
                    )
                    await connection.execute(
                        '''
                        INSERT INTO currencies (currency_id, currency)
                        VALUES (?, ?)
                        ''',
                        (1, 'USD'),
                    )
                    await connection.execute(
                        '''
                        INSERT INTO accounts (
                            account_id, email, name, language_code,
                            language_style, password_hash
                        )
                        VALUES (?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?)
                        ''',
                        (
                            7,
                            'legacy@example.com',
                            'Legacy account',
                            'en',
                            'friendly',
                            'legacy-hash',
                            13,
                            'second@example.com',
                            'Second account',
                            'en',
                            'professional',
                            'second-hash',
                        ),
                    )
                    await connection.execute(
                        '''
                        INSERT INTO action_history (
                            action_id, account_id, ticker_id, currency_id,
                            action, quantity, price, timestamp
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''',
                        (
                            29,
                            7,
                            1,
                            1,
                            'BUY',
                            2,
                            150.5,
                            '2026-01-15',
                        ),
                    )
                    await connection.execute(
                        '''
                        INSERT INTO account_custom_reports (
                            account_id, position, metric
                        )
                        VALUES (?, ?, ?)
                        ''',
                        (7, 0, 'pe_ratio'),
                    )
                    await connection.execute(
                        '''
                        INSERT INTO account_watchlist (
                            account_id, position, is_empty, ticker_id,
                            rendering_mode, llm_explanation
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        ''',
                        (7, 0, 0, 1, 'classic', 1),
                    )

                self.assertTrue(
                    await account_storage.migrate_account_schema()
                )

                async with pool.connection() as connection:
                    accounts = (
                        await connection.execute(
                            '''
                            SELECT account_id, email, role
                            FROM accounts
                            ORDER BY email
                            '''
                        )
                    ).fetchall()
                    account_ids = {
                        str(row['email']): str(row['account_id'])
                        for row in accounts
                    }
                    self.assertEqual(len(account_ids), 2)
                    self.assertEqual(
                        len(set(account_ids.values())),
                        2,
                    )
                    for row in accounts:
                        self.assertEqual(row['role'], 'user')
                        self.assertEqual(
                            UUID(str(row['account_id'])).version,
                            4,
                        )

                    for table_name in (
                        'accounts',
                        'action_history',
                        'account_custom_reports',
                        'account_watchlist',
                    ):
                        table_columns = {
                            str(row['name']): row
                            for row in (
                                await connection.execute(
                                    f'PRAGMA table_info({table_name})'
                                )
                            ).fetchall()
                        }
                        self.assertEqual(
                            table_columns['account_id']['type'],
                            'TEXT',
                        )
                        if table_name != 'accounts':
                            self.assertEqual(
                                int(table_columns['account_id']['notnull']),
                                1,
                            )

                    action = (
                        await connection.execute(
                            '''
                            SELECT account_id, action_id, action, quantity,
                                   price, timestamp
                            FROM action_history
                            '''
                        )
                    ).fetchone()
                    custom_report = (
                        await connection.execute(
                            '''
                            SELECT account_id, position, metric
                            FROM account_custom_reports
                            '''
                        )
                    ).fetchone()
                    watchlist = (
                        await connection.execute(
                            '''
                            SELECT account_id, position, ticker_id,
                                   rendering_mode, llm_explanation
                            FROM account_watchlist
                            '''
                        )
                    ).fetchone()
                    foreign_key_violations = (
                        await connection.execute(
                            'PRAGMA foreign_key_check'
                        )
                    ).fetchall()

                migrated_id: str = account_ids['legacy@example.com']
                self.assertEqual(action['account_id'], migrated_id)
                self.assertEqual(action['action_id'], 29)
                self.assertEqual(action['action'], 'BUY')
                self.assertEqual(action['quantity'], 2)
                self.assertEqual(action['price'], 150.5)
                self.assertEqual(action['timestamp'], '2026-01-15')
                self.assertEqual(custom_report['account_id'], migrated_id)
                self.assertEqual(custom_report['metric'], 'pe_ratio')
                self.assertEqual(watchlist['account_id'], migrated_id)
                self.assertEqual(watchlist['ticker_id'], 1)
                self.assertEqual(watchlist['llm_explanation'], 1)
                self.assertEqual(foreign_key_violations, [])
                self.assertFalse(
                    await account_storage.migrate_account_schema()
                )
            finally:
                account_storage.DATABASE_PATH = original_account_path
                await close_database_pools()

    async def test_unsupported_legacy_schema_fails_without_replacing_data(
        self,
    ) -> None:
        original_account_path: str | Path = account_storage.DATABASE_PATH

        with tempfile.TemporaryDirectory() as directory:
            database_path: Path = Path(directory) / 'unsupported.sqlite3'
            account_storage.DATABASE_PATH = database_path
            try:
                pool = await get_database_pool(
                    database_path,
                    auth_token=DB_AUTH_TOKEN,
                    size=DB_POOL_SIZE,
                    acquire_timeout=DB_POOL_TIMEOUT,
                )
                async with pool.transaction() as connection:
                    await _create_legacy_schema(
                        connection,
                        extra_account_column=True,
                    )
                    await connection.execute(
                        '''
                        INSERT INTO accounts (
                            account_id, email, name, language_code,
                            language_style, password_hash, unexpected
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''',
                        (
                            7,
                            'legacy@example.com',
                            'Legacy account',
                            'en',
                            'friendly',
                            'legacy-hash',
                            'preserve me',
                        ),
                    )

                with self.assertRaises(AccountSchemaException):
                    await account_storage.migrate_account_schema()

                async with pool.connection() as connection:
                    legacy_account = (
                        await connection.execute(
                            '''
                            SELECT account_id, unexpected
                            FROM accounts
                            WHERE email = ?
                            ''',
                            ('legacy@example.com',),
                        )
                    ).fetchone()
                self.assertEqual(legacy_account['account_id'], 7)
                self.assertEqual(legacy_account['unexpected'], 'preserve me')
            finally:
                account_storage.DATABASE_PATH = original_account_path
                await close_database_pools()


if __name__ == '__main__':
    unittest.main()
