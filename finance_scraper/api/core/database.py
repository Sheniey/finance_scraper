
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from finance.config import DB_POOL_SIZE, DB_POOL_TIMEOUT
from finance.services.database import (
    AsyncClientPool,
    AsyncDatabaseConnection,
    AsyncDatabaseTransaction,
    get_database_pool,
)

from api.core.config import settings


def _database_path() -> Path:
    return settings.api.database_path


async def get_api_database_pool() -> AsyncClientPool:
    path: Path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return await get_database_pool(
        path,
        auth_token=None,
        size=DB_POOL_SIZE,
        acquire_timeout=DB_POOL_TIMEOUT,
    )


@asynccontextmanager
async def api_connection() -> AsyncGenerator[AsyncDatabaseConnection, None]:
    pool: AsyncClientPool = await get_api_database_pool()
    async with pool.connection() as connection:
        yield connection


@asynccontextmanager
async def api_transaction() -> AsyncGenerator[AsyncDatabaseTransaction, None]:
    pool: AsyncClientPool = await get_api_database_pool()
    async with pool.transaction() as transaction:
        yield transaction


async def initialize_api_database() -> None:
    async with api_transaction() as connection:
        await connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS api_tokens (
                jti TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                token_type TEXT NOT NULL
                    CHECK (token_type IN ('access', 'refresh')),
                issued_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                revoked_at INTEGER
            )
            ''',
        )
        await connection.execute(
            '''
            CREATE INDEX IF NOT EXISTS idx_api_tokens_session
            ON api_tokens (session_id, token_type, revoked_at)
            ''',
        )
        await connection.execute(
            '''
            CREATE INDEX IF NOT EXISTS idx_api_tokens_account
            ON api_tokens (account_id, token_type, revoked_at)
            ''',
        )
        await connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS api_google_accounts (
                account_id TEXT PRIMARY KEY,
                google_email TEXT NOT NULL,
                scopes_json TEXT NOT NULL,
                connected_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            ''',
        )
        await connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS api_schedules (
                schedule_id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                tickers_json TEXT NOT NULL,
                report_format TEXT NOT NULL,
                run_at TEXT NOT NULL,
                timezone TEXT NOT NULL,
                explain INTEGER NOT NULL CHECK (explain IN (0, 1)),
                mode TEXT NOT NULL,
                charts INTEGER NOT NULL CHECK (charts IN (0, 1)),
                ml_horizon INTEGER NOT NULL,
                enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
                last_run_date TEXT,
                last_run_status TEXT,
                last_error TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            ''',
        )
        await connection.execute(
            '''
            CREATE INDEX IF NOT EXISTS idx_api_schedules_owner
            ON api_schedules (account_id, enabled, run_at)
            ''',
        )
        await connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS api_schedule_runs (
                schedule_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                scheduled_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN (
                        'IN_PROGRESS',
                        'SENDING',
                        'SENT',
                        'FAILED',
                        'DELIVERY_UNKNOWN'
                    )
                ),
                report_ids_json TEXT NOT NULL DEFAULT '[]',
                error_code TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (schedule_id, scheduled_date)
            )
            ''',
        )
