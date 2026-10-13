import asyncio
from pathlib import Path

from finance.services.database import close_database_pools, get_database_pool

import finance.services.account.db as account_database


def test_fresh_local_account_database_is_initialized_without_turso(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path: Path = tmp_path / 'accounts.sqlite3'
    database_key: str = str(database_path.resolve())
    monkeypatch.setattr(account_database, 'DATABASE_PATH', database_path)
    monkeypatch.setattr(account_database, 'REMOTE_URL', '')
    account_database._schema_ready.discard(database_key)

    async def local_pool():
        return await get_database_pool(database_path)

    monkeypatch.setattr(account_database, '_pool', local_pool)

    async def scenario() -> None:
        try:
            await account_database.initialize_account_database()
            pool = await get_database_pool(database_path)
            async with pool.connection() as connection:
                result = await connection.execute(
                    '''
                    SELECT name FROM sqlite_schema
                    WHERE type = 'table'
                    ''',
                )
                table_names: set[str] = {
                    str(row['name'])
                    for row in result.fetchall()
                }
            assert {
                'languages',
                'tickers',
                'currencies',
                'accounts',
                'action_history',
                'account_custom_reports',
                'account_watchlist',
            }.issubset(table_names)
        finally:
            account_database._schema_ready.discard(database_key)
            await close_database_pools()

    asyncio.run(scenario())
