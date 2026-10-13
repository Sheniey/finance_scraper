# ================================================== #
# MODULE: test_account_repository
# ================================================== #

import tempfile
import unittest
from pathlib import Path
from uuid import UUID

from finance.config import DB_AUTH_TOKEN, DB_POOL_SIZE, DB_POOL_TIMEOUT
from finance_core.security import hash_password
from finance.services.account import (
    Account,
    SQLiteAccountRepository,
    WatchlistItem,
    change_password,
    get_account_by_email,
    get_account_with_password,
    get_account_with_password_by_email,
    get_by_id,
    get_password_hash,
    get_password_hash_by_email,
)
from finance.services.account import db as account_storage
from finance.services.database import close_database_pools, get_database_pool
from finance.services.account.models import Action, Stock


class SQLiteAccountRepositoryTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_accounts_use_normalized_sqlite_tables(self) -> None:
        password = 'test-password'
        original_account_path: Path = account_storage.DATABASE_PATH

        with tempfile.TemporaryDirectory() as directory:
            database_path: Path = Path(directory) / 'accounts.sqlite3'
            account_storage.DATABASE_PATH = database_path
            try:
                await account_storage.reset_account_schema()
                await account_storage.import_accounts(
                    [
                        Account(
                            name='Imported account',
                            email='imported@example.com',
                            role='analyst',
                            custom_report=['pe_ratio', 'roic'],
                            watchlist=[
                                WatchlistItem(
                                    ticker='AAPL',
                                    llm_explanation=True,
                                )
                            ],
                            portfolio=[
                                Stock(
                                    ticker='AAPL',
                                    region='US',
                                    currency='USD',
                                    actions=[
                                        Action(
                                            action='BUY',
                                            price=150,
                                            quantity=2,
                                            date='2026-01-15',
                                        )
                                    ],
                                )
                            ],
                        )
                    ],
                    hash_password(password),
                )
                repository = SQLiteAccountRepository()

                pool = await get_database_pool(
                    database_path,
                    auth_token=DB_AUTH_TOKEN,
                    size=DB_POOL_SIZE,
                    acquire_timeout=DB_POOL_TIMEOUT,
                )
                pool.metrics.enabled = True
                pool.metrics.commands = 0
                pool.metrics.rows = 0
                pool.metrics.elapsed_seconds = 0.0
                self.assertEqual(len(await repository.get_everyone()), 1)
                self.assertEqual(pool.metrics.snapshot().commands, 4)
                imported = await repository.get_by_email(
                    'IMPORTED@example.com',
                    password,
                )
                self.assertIsNotNone(imported)
                assert imported is not None
                self.assertEqual(imported.role, 'analyst')
                self.assertIsInstance(imported.account_id, UUID)
                assert imported.account_id is not None
                imported_by_id = await account_storage.get_account(
                    imported.account_id,
                )
                imported_by_id_string = await get_by_id(
                    str(imported.account_id),
                )
                imported_by_email = await get_account_by_email(
                    str(imported.email),
                )
                imported_by_email_compat = await account_storage.get_account(
                    str(imported.email),
                )
                account_with_password, stored_password_hash = (
                    await get_account_with_password(imported.account_id)
                )
                account_with_password_by_email, email_password_hash = (
                    await get_account_with_password_by_email(
                        str(imported.email),
                    )
                )
                self.assertIsNotNone(stored_password_hash)
                self.assertIsNotNone(email_password_hash)
                self.assertEqual(
                    await get_password_hash(imported.account_id),
                    stored_password_hash,
                )
                self.assertEqual(
                    await get_password_hash_by_email(
                        str(imported.email),
                    ),
                    email_password_hash,
                )
                for account_lookup in (
                    imported_by_id,
                    imported_by_id_string,
                    imported_by_email,
                    imported_by_email_compat,
                    account_with_password,
                    account_with_password_by_email,
                ):
                    self.assertIsNotNone(account_lookup)
                    assert account_lookup is not None
                    self.assertEqual(
                        account_lookup.account_id,
                        imported.account_id,
                    )
                named = await repository.get_by_name(
                    'IMPORTED ACCOUNT',
                    password,
                )
                self.assertIsNotNone(named)
                self.assertEqual(imported.custom_report, ['pe_ratio', 'roic'])
                self.assertEqual(imported.watchlist[0].ticker, 'AAPL')
                self.assertEqual(imported.portfolio[0].ticker, 'AAPL')
                self.assertEqual(imported.portfolio[0].actions[0].date, '2026-01-15')
                imported.role = 'admin'
                updated = await repository.update(imported)
                self.assertEqual(updated.role, 'admin')
                self.assertEqual(updated.account_id, imported.account_id)
                updated_from_database = await repository.get_by_email(
                    'imported@example.com',
                    password,
                )
                self.assertIsNotNone(updated_from_database)
                assert updated_from_database is not None
                self.assertEqual(updated_from_database.role, 'admin')
                self.assertEqual(
                    updated_from_database.id,
                    updated_from_database.account_id,
                )
                renamed_account = updated_from_database.model_copy(
                    update={'email': 'renamed@example.com'},
                )
                updated_email_account = await repository.update(renamed_account)
                self.assertEqual(
                    str(updated_email_account.email),
                    'renamed@example.com',
                )
                self.assertIsNone(
                    await repository.get_by_email(
                        'imported@example.com',
                        password,
                    ),
                )
                assert updated_email_account.account_id is not None
                self.assertTrue(
                    await change_password(
                        updated_email_account.account_id,
                        password,
                        'updated-password',
                    ),
                )
                self.assertIsNone(
                    await repository.get_by_email(
                        'renamed@example.com',
                        password,
                    ),
                )
                self.assertIsNotNone(
                    await repository.get_by_email(
                        'renamed@example.com',
                        'updated-password',
                    ),
                )
                created_account = await repository.create(
                    Account(
                        name='SQLite test account',
                        email='sqlite-test@example.com',
                    ),
                    password,
                )
                self.assertIsInstance(created_account.account_id, UUID)
                assert created_account.account_id is not None
                self.assertEqual(len(await repository.get_everyone()), 2)

                pool = await get_database_pool(database_path)
                async with pool.connection() as connection:
                    account_columns = {
                        str(row['name']): row
                        for row in (
                            await connection.execute(
                                'PRAGMA table_info(accounts)'
                            )
                        ).fetchall()
                    }
                    columns = set(account_columns)
                    tables = {
                        row['name']
                        for row in (
                            await connection.execute(
                                "SELECT name FROM sqlite_master WHERE type = 'table'"
                            )
                        ).fetchall()
                    }
                    action_count = (
                        await connection.execute(
                            'SELECT COUNT(*) FROM action_history'
                        )
                    ).fetchone()['COUNT(*)']
                    watchlist_columns = {
                        row['name']
                        for row in (
                            await connection.execute(
                                'PRAGMA table_info(account_watchlist)'
                            )
                        ).fetchall()
                    }
                    watchlist_account_id_type = next(
                        str(row['type'])
                        for row in (
                            await connection.execute(
                                'PRAGMA table_info(account_watchlist)'
                            )
                        ).fetchall()
                        if row['name'] == 'account_id'
                    )
                    account_ids = (
                        await connection.execute(
                            'SELECT account_id FROM accounts'
                        )
                    ).fetchall()
                self.assertNotIn('portfolio', columns)
                self.assertEqual(account_columns['account_id']['type'], 'TEXT')
                self.assertEqual(account_columns['role']['type'], 'TEXT')
                self.assertEqual(
                    account_columns['role']['dflt_value'],
                    "'user'",
                )
                self.assertEqual(watchlist_account_id_type, 'TEXT')
                self.assertEqual(len(account_ids), 2)
                for row in account_ids:
                    self.assertEqual(UUID(str(row['account_id'])).version, 4)

                deleted_by_legacy_email = await account_storage.delete_account(
                    'renamed@example.com',
                )
                self.assertIsNotNone(deleted_by_legacy_email)
                assert deleted_by_legacy_email is not None
                self.assertEqual(
                    deleted_by_legacy_email.account_id,
                    imported.account_id,
                )
                deleted_by_uuid = await account_storage.delete_account(
                    created_account.account_id,
                )
                self.assertIsNotNone(deleted_by_uuid)
                assert deleted_by_uuid is not None
                self.assertEqual(
                    deleted_by_uuid.account_id,
                    created_account.account_id,
                )
                assert created_account.account_id is not None
                self.assertIsNone(
                    await account_storage.get_account(
                        created_account.account_id,
                    )
                )
                self.assertIn('action_history', tables)
                self.assertEqual(action_count, 1)
                self.assertNotIn('charts', watchlist_columns)
                self.assertNotIn('horizon', watchlist_columns)
                self.assertNotIn('enabled', watchlist_columns)
                await close_database_pools()
            finally:
                account_storage.DATABASE_PATH = original_account_path
                await close_database_pools()


if __name__ == '__main__':
    unittest.main()
