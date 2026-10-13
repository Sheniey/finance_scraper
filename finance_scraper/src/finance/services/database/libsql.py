"""Async facade and bounded pool for the official libSQL Python driver."""

import sqlite3
import os, asyncio
import hashlib
import re, logging, time
from _thread import LockType
from collections.abc import AsyncIterator, Callable, Iterable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any
from urllib.parse import unquote, urlparse

from finance.services.database.exceptions import (
    DatabaseConfigurationError,
    DatabaseException,
    DatabaseIntegrityError,
    DatabaseSyncError,
)
from finance.services.database.sync import (
    SyncFileLock,
    SyncStats,
    acquire_sync_file_lock,
    open_turso_sync_connection,
    sync_marker_path,
    validate_sync_url,
)


# ================================================== #
# TYPES                                              #
# ================================================== #

logger: logging.Logger = logging.getLogger(__name__)
type Rows = list[LibSQLRow]
type Columns = tuple[str, ...]
type SQLParameters = Sequence[Any] | dict[str, Any] | None
type SQLStatement = tuple[str, SQLParameters]
type SyncConnection = Any


class LibSQLRow(dict[str, Any]):
    """Mapping row compatible with application repositories."""


@dataclass(frozen=True, slots=True)
class DatabaseMetricSnapshot:
    """Optional aggregate metrics for one pool lifecycle."""

    commands: int
    rows: int
    elapsed_seconds: float


class DatabaseMetrics:
    """Low-overhead query metrics, enabled only by DB_PROFILE."""

    def __init__(self, enabled: bool = False) -> None:
        self.enabled: bool = enabled
        self.commands: int = 0
        self.rows: int = 0
        self.elapsed_seconds: float = 0.0

    def record(
        self,
        label: str,
        rows: int,
        elapsed_seconds: float,
    ) -> None:
        if not self.enabled:
            return
        self.commands += 1
        self.rows += rows
        self.elapsed_seconds += elapsed_seconds
        logger.debug(
            'db query label=%s rows=%d elapsed=%.4fs',
            label,
            rows,
            elapsed_seconds,
        )

    def snapshot(self) -> DatabaseMetricSnapshot:
        return DatabaseMetricSnapshot(
            commands=self.commands,
            rows=self.rows,
            elapsed_seconds=self.elapsed_seconds,
        )


def _statement_label(statement: str) -> str:
    normalized: str = re.sub(r'\s+', ' ', statement).strip()
    return normalized[:100]


async def _acquire_process_lock(lock: LockType) -> None:
    acquire_task: asyncio.Task[bool] = asyncio.create_task(
        asyncio.to_thread(lock.acquire),
    )
    try:
        await asyncio.shield(acquire_task)
    except asyncio.CancelledError:
        await acquire_task
        lock.release()
        raise


async def _run_with_process_lock(
    lock: LockType,
    operation: Callable[[], Any],
) -> Any:
    await _acquire_process_lock(lock)
    operation_task: asyncio.Task[Any] = asyncio.create_task(
        asyncio.to_thread(operation),
    )
    try:
        try:
            return await asyncio.shield(operation_task)
        except asyncio.CancelledError:
            await operation_task
            raise
    finally:
        lock.release()


# ================================================== #
# URL AND DRIVER HELPERS                             #
# ================================================== #

def database_url(database: str | Path) -> str:
    """Normalize local paths and both Turso remote URL formats."""

    if isinstance(database, Path):
        return f'file:{database.resolve().as_posix()}'

    value: str = database.strip()
    if not value:
        raise DatabaseConfigurationError('Database URL must not be blank')

    # detect absolute Windows paths, e.g. C:\data\accounts.db
    if re.match(r'^[a-zA-Z]:[\\/]', value):
        return f'file:{Path(value).resolve().as_posix()}'
    
    parsed = urlparse(value)
    if not parsed.scheme:
        return f'file:{Path(value).resolve().as_posix()}'

    if parsed.scheme in {'http', 'https', 'libsql', 'wss'} and (
        parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise DatabaseConfigurationError(
            'Remote database URLs must not contain credentials or query parameters.',
        )

    match parsed.scheme:
        case '':
            return f'file:{Path(value).resolve().as_posix()}'
        case 'file':
            return value
        case 'http'|'https':
            return value
        case 'libsql'|'wss':
            return parsed._replace(scheme='https').geturl()
        case 'ws':
            raise DatabaseConfigurationError(
                'Remote DB_LOCATION must use https:// or libsql://; '
                'unencrypted ws:// is not supported',
            )
        case _:
            raise DatabaseConfigurationError(
                f'Unsupported DB_LOCATION scheme: {parsed.scheme!r}',
            )


def _local_path(url: str) -> str:
    parsed = urlparse(url)
    path: str = unquote(parsed.path)
    if (
        os.name == 'nt'
        and len(path) > 2
        and path.startswith('/')
        and path[2] == ':'
    ):
        path = path[1:]
    if parsed.netloc and parsed.netloc != 'localhost':
        path = f'//{parsed.netloc}{path}'
    return path


def _open_connection(
    url: str,
    auth_token: str | None,
    *,
    sync_remote_url: str | None = None,
) -> SyncConnection:
    if sync_remote_url is not None:
        if not url.startswith('file:'):
            raise DatabaseConfigurationError(
                'Turso Sync requires a local database file path.',
            )
        return open_turso_sync_connection(
            _local_path(url),
            sync_remote_url,
            auth_token,
        )

    if url.startswith('file:'):
        path = _local_path(url)
        return sqlite3.connect(
            path,
            check_same_thread=False,
            timeout=30,
            isolation_level=None,
        )

    import libsql

    return libsql.connect(
        url,
        auth_token=auth_token or '',
    )


def _translate_error(error: Exception) -> DatabaseException:
    message: str = str(error)
    lowered: str = message.lower()
    if isinstance(error, sqlite3.IntegrityError) or 'constraint' in lowered:
        return DatabaseIntegrityError(message)
    if isinstance(
        error,
        (OSError, TimeoutError, ConnectionError, sqlite3.Error),
    ):
        return DatabaseException(message)
    if error.__class__.__module__.startswith('libsql'):
        return DatabaseException(message)
    if error.__class__.__module__.startswith('turso'):
        return DatabaseException('Turso Sync database operation failed.')
    raise error


def _raise_database_error(e: Exception) -> None:
    translated: DatabaseException = _translate_error(e)
    raise translated from e


def _execute_sync(
    connection: SyncConnection,
    statement: str,
    parameters: SQLParameters,
) -> 'AsyncDatabaseResult':
    cursor = (
        connection.execute(statement)
        if parameters is None
        else connection.execute(statement, parameters)
    )
    description: Any = getattr(cursor, 'description', None)
    columns: Columns = (
        tuple(column[0] for column in description)
        if description is not None
        else ()
    )
    fetched_rows: Iterable[Any] = cursor.fetchall() or ()
    return AsyncDatabaseResult(
        columns=columns,
        rows=fetched_rows,
        rowcount=int(getattr(cursor, 'rowcount', -1)),
        lastrowid=getattr(cursor, 'lastrowid', None),
    )


# ================================================== #
# RESULT ADAPTER                                      #
# ================================================== #

class AsyncDatabaseResult:
    """Compatibility wrapper around sync libSQL cursor results."""

    def __init__(
        self,
        *,
        columns: Columns,
        rows: Iterable[Any],
        rowcount: int,
        lastrowid: int | None,
    ) -> None:
        self.__columns: Columns = columns
        self.__rows: Rows = [
            LibSQLRow(zip(self.__columns, row))
            for row in rows
        ]
        self.__position: int = 0
        self.__rowcount: int = rowcount
        self.__lastrowid: int | None = (
            int(lastrowid)
            if lastrowid is not None
            else None
        )

    def __iter__(self) -> Iterable[LibSQLRow]:
        return iter(self.__rows)

    def fetchone(self) -> LibSQLRow | None:
        if self.__position >= len(self.__rows):
            return None
        row: LibSQLRow = self.__rows[self.__position]
        self.__position += 1
        return row

    def fetchall(self) -> Rows:
        rows: Rows = self.__rows[self.__position:]
        self.__position = len(self.__rows)
        return rows

    @property
    def rows(self) -> Rows:
        return self.__rows

    @property
    def columns(self) -> Columns:
        return self.__columns

    @property
    def rowcount(self) -> int:
        return self.__rowcount

    @property
    def lastrowid(self) -> int | None:
        return self.__lastrowid


# ================================================== #
# CONNECTION AND TRANSACTION ADAPTERS                #
# ================================================== #

class AsyncDatabaseConnection:
    """Async facade that moves blocking libSQL calls to worker threads."""

    def __init__(
        self,
        client: SyncConnection,
        metrics: DatabaseMetrics | None = None,
    ) -> None:
        self.__client: SyncConnection = client
        self.__metrics: DatabaseMetrics | None = metrics

    async def execute(
        self,
        statement: str,
        parameters: SQLParameters = None,
    ) -> AsyncDatabaseResult:
        started_at: float = time.perf_counter()
        try:
            result: AsyncDatabaseResult = await asyncio.to_thread(
                _execute_sync,
                self.__client,
                statement,
                parameters,
            )
        except Exception as e:
            _raise_database_error(e)
        if self.__metrics is not None:
            self.__metrics.record(
                _statement_label(statement),
                len(result.rows),
                time.perf_counter() - started_at,
            )
        return result

    async def batch(
        self,
        statements: Sequence[SQLStatement],
    ) -> list[AsyncDatabaseResult]:
        started_at: float = time.perf_counter()

        def run_batch() -> list[AsyncDatabaseResult]:
            return [
                _execute_sync(self.__client, statement, parameters)
                for statement, parameters in statements
            ]

        try:
            results: list[AsyncDatabaseResult] = await asyncio.to_thread(
                run_batch,
            )
        except Exception as e:
            _raise_database_error(e)
        if self.__metrics is not None:
            elapsed_seconds: float = time.perf_counter() - started_at
            per_statement: float = (
                elapsed_seconds / len(results)
                if results
                else elapsed_seconds
            )
            for (statement, _), result in zip(statements, results):
                self.__metrics.record(
                    _statement_label(statement),
                    len(result.rows),
                    per_statement,
                )
        return results

    def transaction(self) -> 'AsyncDatabaseTransaction':
        return AsyncDatabaseTransaction(self.__client, self.__metrics)


class AsyncDatabaseTransaction:
    """Transaction facade that preserves async callers over sync libSQL."""

    def __init__(
        self,
        client: SyncConnection,
        metrics: DatabaseMetrics | None = None,
    ) -> None:
        self.__client: SyncConnection = client
        self.__metrics: DatabaseMetrics | None = metrics
        self.__closed: bool = False

    async def begin(self) -> None:
        await asyncio.to_thread(self.__client.execute, 'BEGIN')

    async def execute(
        self,
        statement: str,
        parameters: SQLParameters = None,
    ) -> AsyncDatabaseResult:
        if self.__closed:
            raise DatabaseException('The database transaction is closed')
        started_at: float = time.perf_counter()
        try:
            result: AsyncDatabaseResult = await asyncio.to_thread(
                _execute_sync,
                self.__client,
                statement,
                parameters,
            )
        except Exception as e:
            _raise_database_error(e)
        if self.__metrics is not None:
            self.__metrics.record(
                _statement_label(statement),
                len(result.rows),
                time.perf_counter() - started_at,
            )
        return result

    async def commit(self) -> None:
        if not self.__closed:
            await asyncio.to_thread(self.__client.commit)
            self.__closed = True

    async def rollback(self) -> None:
        if not self.__closed:
            await asyncio.to_thread(self.__client.rollback)
            self.__closed = True

    def close(self) -> None:
        self.__closed = True


# ================================================== #
# CLIENT POOL                                        #
# ================================================== #

class AsyncClientPool:
    """Bounded pool of local SQLite, libSQL, or Turso Sync connections."""

    def __init__(
        self,
        database: str | Path,
        *,
        auth_token: str | None = None,
        sync_remote_url: str | None = None,
        require_sync_marker: bool = True,
        size: int = 2,
        acquire_timeout: float = 5.0,
    ) -> None:
        if size <= 0:
            raise ValueError('Database pool size must be positive')
        if acquire_timeout <= 0:
            raise ValueError('Database pool timeout must be positive')

        self.url: str = database_url(database)
        self.__auth_token: str | None = auth_token
        self.sync_remote_url: str | None = (
            validate_sync_url(sync_remote_url)
            if sync_remote_url is not None
            else None
        )
        if self.sync_remote_url is not None and not self.url.startswith('file:'):
            raise DatabaseConfigurationError(
                'Turso Sync requires a local database file path.',
            )
        self.__require_sync_marker: bool = require_sync_marker
        self.size: int = size
        self.acquire_timeout: float = acquire_timeout
        self.metrics: DatabaseMetrics = DatabaseMetrics(
            os.getenv('DB_PROFILE', '').strip().lower()
            in {'1', 'true', 'yes', 'on'}
        )
        self.__clients: list[SyncConnection] = []
        self.__sync_client: SyncConnection | None = None
        self.__file_lock: SyncFileLock | None = None
        self.__replica_operation_lock: LockType | None = None
        self.__available: asyncio.LifoQueue[SyncConnection] = asyncio.LifoQueue()
        self.__start_lock: asyncio.Lock | None = None
        self.__write_lock: asyncio.Lock = asyncio.Lock()
        self.__sync_lock: asyncio.Lock = asyncio.Lock()
        self.__loop: asyncio.AbstractEventLoop | None = None
        self.__started: bool = False
        self.__closed: bool = False

    async def start(self) -> None:
        current_loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        if self.__loop is not None and self.__loop is not current_loop:
            raise DatabaseException(
                'Database pool cannot be shared across event loops',
            )
        if self.__started:
            return
        if self.__start_lock is None:
            self.__start_lock = asyncio.Lock()
        async with self.__start_lock:
            if self.__started:
                return
            if self.__closed:
                raise DatabaseException('Database pool is closed')
            self.__loop = current_loop
            try:
                if self.sync_remote_url is not None:
                    local_path: str = _local_path(self.url)
                    if (
                        self.__require_sync_marker
                        and not sync_marker_path(local_path).is_file()
                    ):
                        raise DatabaseConfigurationError(
                            'The local file is not marked as a Turso Sync replica; '
                            'run the local migration command first.',
                        )
                    self.__file_lock = acquire_sync_file_lock(local_path)
                    self.__replica_operation_lock = (
                        self.__file_lock.operation_lock
                    )

                for _ in range(self.size):
                    self.__clients.append(
                        await asyncio.to_thread(
                            _open_connection,
                            self.url,
                            self.__auth_token,
                            sync_remote_url=self.sync_remote_url,
                        )
                    )

                if self.sync_remote_url is not None:
                    self.__sync_client = await asyncio.to_thread(
                        _open_connection,
                        self.url,
                        self.__auth_token,
                        sync_remote_url=self.sync_remote_url,
                    )

                for client in self.__clients:
                    await self.__available.put(client)
            except Exception as e:
                for client in self.__clients:
                    await asyncio.to_thread(client.close)
                self.__clients.clear()
                if self.__sync_client is not None:
                    await asyncio.to_thread(self.__sync_client.close)
                    self.__sync_client = None
                if self.__file_lock is not None:
                    self.__file_lock.release()
                    self.__file_lock = None
                    self.__replica_operation_lock = None
                _raise_database_error(e)
            self.__started = True

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[AsyncDatabaseConnection]:
        await self.start()
        replica_operation_lock: LockType | None = (
            self.__replica_operation_lock
        )
        if self.sync_remote_url is not None:
            if replica_operation_lock is None:
                raise DatabaseException(
                    'The local Turso Sync process lock is unavailable.',
                )
            await _acquire_process_lock(replica_operation_lock)
        has_connection: bool = False
        try:
            client: SyncConnection = await asyncio.wait_for(
                self.__available.get(),
                timeout=self.acquire_timeout,
            )
            has_connection = True
        except asyncio.TimeoutError as e:
            raise DatabaseException(
                'Timed out waiting for a database connection',
            ) from e
        finally:
            if not has_connection and replica_operation_lock is not None:
                replica_operation_lock.release()

        try:
            yield AsyncDatabaseConnection(client, self.metrics)
        finally:
            try:
                await self.__available.put(client)
            finally:
                if replica_operation_lock is not None:
                    replica_operation_lock.release()

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncDatabaseTransaction]:
        local_write: bool = self.url.startswith('file:')
        if local_write:
            await self.__write_lock.acquire()
        try:
            async with self.connection() as connection:
                transaction: AsyncDatabaseTransaction = connection.transaction()
                try:
                    await transaction.begin()
                    yield transaction
                    await transaction.commit()
                except BaseException:
                    await transaction.rollback()
                    raise
                finally:
                    transaction.close()
        finally:
            if local_write:
                self.__write_lock.release()

    @property
    def is_turso_sync(self) -> bool:
        return self.sync_remote_url is not None

    async def pull(self) -> bool:
        client: SyncConnection = await self._sync_connection()
        async with self.__sync_lock:
            operation_lock: LockType | None = (
                self.__replica_operation_lock
            )
            if operation_lock is None:
                raise DatabaseException(
                    'The local Turso Sync process lock is unavailable.',
                )
            try:
                return bool(
                    await _run_with_process_lock(operation_lock, client.pull),
                )
            except Exception as e:
                raise DatabaseSyncError(
                    'Turso pull failed; local data remains available.',
                ) from e

    async def push(self) -> None:
        client: SyncConnection = await self._sync_connection()
        async with self.__sync_lock:
            operation_lock: LockType | None = (
                self.__replica_operation_lock
            )
            if operation_lock is None:
                raise DatabaseException(
                    'The local Turso Sync process lock is unavailable.',
                )
            try:
                await _run_with_process_lock(operation_lock, client.push)
            except Exception as e:
                raise DatabaseSyncError(
                    'Turso push failed; local changes remain pending.',
                ) from e

    async def sync_stats(self) -> SyncStats:
        client: SyncConnection = await self._sync_connection()
        async with self.__sync_lock:
            operation_lock: LockType | None = (
                self.__replica_operation_lock
            )
            if operation_lock is None:
                raise DatabaseException(
                    'The local Turso Sync process lock is unavailable.',
                )
            try:
                stats = await _run_with_process_lock(
                    operation_lock,
                    client.stats,
                )
            except Exception as e:
                _raise_database_error(e)
        revision: object | None = stats.revision
        return SyncStats(
            cdc_operations=int(stats.cdc_operations),
            last_pull_unix_time=stats.last_pull_unix_time,
            last_push_unix_time=stats.last_push_unix_time,
            main_wal_size=int(stats.main_wal_size),
            network_received_bytes=int(stats.network_received_bytes),
            network_sent_bytes=int(stats.network_sent_bytes),
            revert_wal_size=int(stats.revert_wal_size),
            revision=str(revision) if revision is not None else None,
        )

    async def _sync_connection(self) -> SyncConnection:
        if self.sync_remote_url is None:
            raise DatabaseConfigurationError(
                'This database pool is not configured for Turso Sync.',
            )
        await self.start()
        if self.__sync_client is None:
            raise DatabaseException('Turso Sync connection is unavailable.')
        return self.__sync_client

    async def close(self) -> None:
        if self.__closed:
            return
        self.__closed = True
        clients: list[SyncConnection] = list(self.__clients)
        self.__clients.clear()
        if self.__sync_client is not None:
            clients.append(self.__sync_client)
            self.__sync_client = None
        try:
            await asyncio.gather(
                *(asyncio.to_thread(client.close) for client in clients)
            )
        finally:
            if self.__file_lock is not None:
                self.__file_lock.release()
                self.__file_lock = None
                self.__replica_operation_lock = None
        self.__started = False
        self.__loop = None

    @property
    def loop(self) -> asyncio.AbstractEventLoop | None:
        return self.__loop


# ================================================== #
# SHARED POOL REGISTRY                               #
# ================================================== #

_POOL_REGISTRY: dict[
    tuple[str, bytes | None, str | None, int, float, bool],
    AsyncClientPool,
] = {}
_POOL_REGISTRY_LOCK: RLock = RLock()


async def get_database_pool(
    database: str | Path,
    *,
    auth_token: str | None = None,
    size: int = 2,
    acquire_timeout: float = 5.0,
) -> AsyncClientPool:
    """Return and start one shared pool for a database configuration."""

    url: str = database_url(database)
    token_digest: bytes | None = (
        hashlib.sha256(auth_token.encode('utf-8')).digest()
        if auth_token is not None
        else None
    )
    key: tuple[str, bytes | None, str | None, int, float, bool] = (
        url,
        token_digest,
        None,
        size,
        acquire_timeout,
        False,
    )
    with _POOL_REGISTRY_LOCK:
        pool: AsyncClientPool | None = _POOL_REGISTRY.get(key)
    current_loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
    if pool is not None and pool.loop not in {None, current_loop}:
        await pool.close()
        with _POOL_REGISTRY_LOCK:
            if _POOL_REGISTRY.get(key) is pool:
                _POOL_REGISTRY.pop(key, None)
        pool = None
    if pool is None:
        with _POOL_REGISTRY_LOCK:
            pool = AsyncClientPool(
                url,
                auth_token=auth_token,
                size=size,
                acquire_timeout=acquire_timeout,
            )
            _POOL_REGISTRY[key] = pool
    await pool.start()
    return pool


async def get_turso_sync_pool(
    database: str | Path,
    *,
    remote_url: str,
    auth_token: str | None,
    size: int = 2,
    acquire_timeout: float = 5.0,
    require_sync_marker: bool = True,
) -> AsyncClientPool:
    """Return and start a pool that opens the local file through Turso Sync."""

    url: str = database_url(database)
    normalized_remote_url: str = validate_sync_url(remote_url)
    token_digest: bytes | None = (
        hashlib.sha256(auth_token.encode('utf-8')).digest()
        if auth_token is not None
        else None
    )
    key: tuple[str, bytes | None, str | None, int, float, bool] = (
        url,
        token_digest,
        normalized_remote_url,
        size,
        acquire_timeout,
        require_sync_marker,
    )
    with _POOL_REGISTRY_LOCK:
        pool: AsyncClientPool | None = _POOL_REGISTRY.get(key)
    current_loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
    if pool is not None and pool.loop not in {None, current_loop}:
        await pool.close()
        with _POOL_REGISTRY_LOCK:
            if _POOL_REGISTRY.get(key) is pool:
                _POOL_REGISTRY.pop(key, None)
        pool = None
    if pool is None:
        with _POOL_REGISTRY_LOCK:
            pool = AsyncClientPool(
                url,
                auth_token=auth_token,
                sync_remote_url=normalized_remote_url,
                require_sync_marker=require_sync_marker,
                size=size,
                acquire_timeout=acquire_timeout,
            )
            _POOL_REGISTRY[key] = pool
    await pool.start()
    return pool


async def push_turso_sync_pools() -> None:
    """Push pending CDC changes from every active Turso Sync pool."""

    with _POOL_REGISTRY_LOCK:
        pools: list[AsyncClientPool] = list(_POOL_REGISTRY.values())
    for pool in pools:
        if pool.is_turso_sync:
            await pool.push()


async def close_database_pools() -> None:
    """Close every shared pool during application shutdown or test cleanup."""

    with _POOL_REGISTRY_LOCK:
        pools: list[AsyncClientPool] = list(_POOL_REGISTRY.values())
        _POOL_REGISTRY.clear()
    for pool in pools:
        await pool.close()


async def sync_and_close_database_pools() -> None:
    """Push local CDC changes before closing CLI-owned database pools."""

    try:
        await push_turso_sync_pools()
    finally:
        await close_database_pools()


__all__: list[str] = [
    'AsyncClientPool',
    'AsyncDatabaseConnection',
    'AsyncDatabaseResult',
    'AsyncDatabaseTransaction',
    'Columns',
    'DatabaseMetricSnapshot',
    'DatabaseMetrics',
    'LibSQLRow',
    'Rows',
    'SQLParameters',
    'SQLStatement',
    'close_database_pools',
    'database_url',
    'get_database_pool',
    'get_turso_sync_pool',
    'push_turso_sync_pools',
    'sync_and_close_database_pools',
]
