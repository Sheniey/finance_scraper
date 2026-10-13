import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from finance.services.database import (
    DatabaseConfigurationError,
    close_database_pools,
    database_url,
    get_database_pool,
)


# ================================================== #
# URL VALIDATION                                     #
# ================================================== #

def test_database_url_accepts_https_and_libsql_remote_schemes() -> None:
    assert database_url('https://database.example.test') == (
        'https://database.example.test'
    )
    assert database_url('libsql://database.example.test') == (
        'https://database.example.test'
    )


def test_database_url_rejects_unencrypted_websocket_scheme() -> None:
    with pytest.raises(DatabaseConfigurationError):
        database_url('ws://database.example.test')


def test_database_url_rejects_embedded_remote_credentials() -> None:
    with pytest.raises(DatabaseConfigurationError):
        database_url('https://token@database.example.test')


def test_database_url_rejects_remote_query_parameters() -> None:
    with pytest.raises(DatabaseConfigurationError):
        database_url('https://database.example.test?authToken=secret')


def test_database_url_normalizes_local_path() -> None:
    with TemporaryDirectory() as directory:
        url = database_url(Path(directory) / 'database.sqlite3')
        assert url.startswith('file:')


# ================================================== #
# ASYNC CLIENT POOL                                  #
# ================================================== #

def test_async_pool_supports_batch_and_transactions() -> None:
    async def scenario() -> None:
        with TemporaryDirectory() as directory:
            pool = await get_database_pool(
                Path(directory) / 'database.sqlite3',
                size=2,
            )
            async with pool.connection() as connection:
                await connection.execute(
                    'CREATE TABLE values_table (id INTEGER PRIMARY KEY, value TEXT)'
                )
                results = await connection.batch(
                    [
                        (
                            'INSERT INTO values_table (value) VALUES (?)',
                            ('one',),
                        ),
                        (
                            'INSERT INTO values_table (value) VALUES (?)',
                            ('two',),
                        ),
                        (
                            'SELECT value FROM values_table ORDER BY id',
                            (),
                        ),
                    ]
                )
                assert results[-1].fetchall() == [
                    {'value': 'one'},
                    {'value': 'two'},
                ]

            async with pool.transaction() as transaction:
                await transaction.execute(
                    'INSERT INTO values_table (value) VALUES (?)',
                    ('three',),
                )

            async with pool.connection() as connection:
                result = await connection.execute(
                    'SELECT COUNT(*) AS count FROM values_table'
                )
                assert result.fetchone()['count'] == 3

            await close_database_pools()

    asyncio.run(scenario())


def test_async_pool_rolls_back_failed_transaction() -> None:
    async def scenario() -> None:
        with TemporaryDirectory() as directory:
            pool = await get_database_pool(Path(directory) / 'database.sqlite3')
            async with pool.transaction() as transaction:
                await transaction.execute(
                    'CREATE TABLE values_table (id INTEGER PRIMARY KEY, value TEXT)'
                )

            with pytest.raises(Exception):
                async with pool.transaction() as transaction:
                    await transaction.execute(
                        'INSERT INTO values_table (id, value) VALUES (?, ?)',
                        (1, 'one'),
                    )
                    await transaction.execute(
                        'INSERT INTO values_table (id, value) VALUES (?, ?)',
                        (1, 'duplicate'),
                    )

            async with pool.connection() as connection:
                result = await connection.execute(
                    'SELECT COUNT(*) AS count FROM values_table'
                )
                assert result.fetchone()['count'] == 0

            await close_database_pools()

    asyncio.run(scenario())
