"""Turso Sync connection helpers and single-process ownership."""

import os, errno
from _thread import LockType
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import Lock, RLock
from typing import Any
from urllib.parse import urlparse

from finance.services.database.exceptions import (
    DatabaseAlreadyOpenError,
    DatabaseConfigurationError,
    DatabaseException,
    DatabaseSyncError,
)


type SyncConnection = Any


@dataclass(slots=True)
class _FileLockState:
    descriptor: int
    references: int
    is_windows: bool
    operation_lock: LockType


@dataclass(frozen=True, slots=True)
class SyncStats:
    cdc_operations: int
    last_pull_unix_time: int | None
    last_push_unix_time: int | None
    main_wal_size: int
    network_received_bytes: int
    network_sent_bytes: int
    revert_wal_size: int
    revision: str | None


_FILE_LOCKS: dict[str, _FileLockState] = {}
_FILE_LOCKS_GUARD: RLock = RLock()
_SYNC_MARKER_CONTENT: str = 'turso-sync-v1\n'


def validate_sync_url(remote_url: str) -> str:
    """
    Validate a URL for a native Turso Sync database.

    Credentials and URL query parameters are rejected because authentication
    must be supplied separately through the database-scoped auth token.
    """

    value: str = remote_url.strip()
    if not value:
        raise DatabaseConfigurationError('DB_LOCATION is required for Turso Sync.')

    try:
        parsed = urlparse(value)
        has_valid_host: bool = bool(parsed.hostname)
        has_valid_port: bool = parsed.port is None or 0 < parsed.port < 65536
    except ValueError as e:
        raise DatabaseConfigurationError(
            'DB_LOCATION must be a valid Turso Sync URL.',
        ) from e

    if (
        parsed.scheme not in {'https', 'turso'}
        or not has_valid_host
        or not has_valid_port
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {'', '/'}
    ):
        raise DatabaseConfigurationError(
            'DB_LOCATION must be an HTTPS or Turso URL without embedded credentials.',
        )

    return value


def sync_marker_path(database_path: str | Path) -> Path:
    path: Path = Path(database_path).expanduser().resolve()
    return Path(f'{path}.sync-managed')


def acquire_sync_file_lock(database_path: str | Path) -> 'SyncFileLock':
    """Acquire a process-wide lock for one local Turso Sync database."""

    path: Path = Path(database_path).expanduser().resolve()
    key: str = os.path.normcase(str(path))
    with _FILE_LOCKS_GUARD:
        existing: _FileLockState | None = _FILE_LOCKS.get(key)
        if existing is not None:
            existing.references += 1
            return SyncFileLock(key)

        lock_path: Path = Path(f'{path}.lock')
        try:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            descriptor: int = os.open(
                lock_path,
                os.O_CREAT | os.O_RDWR,
                0o600,
            )
        except OSError as e:
            raise DatabaseException(
                'Could not create the local Turso Sync process lock.',
            ) from e

        try:
            if os.fstat(descriptor).st_size == 0:
                os.write(descriptor, b'\0')
            _lock_descriptor(descriptor)
        except OSError as e:
            os.close(descriptor)
            if e.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                raise DatabaseAlreadyOpenError(
                    'The local Turso Sync replica is already open in another process.',
                ) from e
            raise DatabaseException(
                'Could not acquire the local Turso Sync process lock.',
            ) from e

        _FILE_LOCKS[key] = _FileLockState(
            descriptor=descriptor,
            references=1,
            is_windows=os.name == 'nt',
            operation_lock=Lock(),
        )

    return SyncFileLock(key)


class SyncFileLock:
    """Hold one reference to the process-wide replica lock."""

    def __init__(self, key: str) -> None:
        self.__key: str = key
        self.__released: bool = False

    def release(self) -> None:
        if self.__released:
            return

        with _FILE_LOCKS_GUARD:
            state: _FileLockState | None = _FILE_LOCKS.get(self.__key)
            self.__released = True
            if state is None:
                return

            state.references -= 1
            if state.references > 0:
                return

            _FILE_LOCKS.pop(self.__key, None)
            try:
                _unlock_descriptor(
                    state.descriptor,
                    is_windows=state.is_windows,
                )
            finally:
                os.close(state.descriptor)

    @property
    def operation_lock(self) -> LockType:
        with _FILE_LOCKS_GUARD:
            state: _FileLockState | None = _FILE_LOCKS.get(self.__key)
            if state is None:
                raise DatabaseException(
                    'The local Turso Sync process lock is no longer active.',
                )
            return state.operation_lock


def _lock_descriptor(descriptor: int) -> None:
    if os.name == 'nt':
        import msvcrt

        os.lseek(descriptor, 0, os.SEEK_SET)
        msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
        return

    import fcntl

    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_descriptor(descriptor: int, *, is_windows: bool) -> None:
    if is_windows:
        import msvcrt

        os.lseek(descriptor, 0, os.SEEK_SET)
        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(descriptor, fcntl.LOCK_UN)


def open_turso_sync_connection(
    database_path: str | Path,
    remote_url: str,
    auth_token: str | None,
) -> SyncConnection:
    """Open the local replica exclusively through the Turso Sync SDK."""

    path: Path = Path(database_path).expanduser().resolve()
    normalized_url: str = validate_sync_url(remote_url)
    if auth_token is None or not auth_token.strip():
        raise DatabaseConfigurationError(
            'DB_AUTH_TOKEN is required for Turso Sync.',
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import turso
        import turso.sync
    except ModuleNotFoundError as e:
        raise DatabaseConfigurationError(
            'pyturso is unavailable; run the API or CLI in Docker/WSL Linux.',
        ) from e

    try:
        connection: SyncConnection = turso.sync.connect(
            path=str(path),
            remote_url=normalized_url,
            auth_token=auth_token.strip(),
            bootstrap_if_empty=False,
        )
        connection.row_factory = turso.Row
        connection.execute('PRAGMA foreign_keys = ON')
        return connection
    except Exception as e:
        raise DatabaseException(
            'Could not open the local Turso Sync replica.',
        ) from e


class TursoSyncDatabase:
    """Provide serialized synchronous access to a Turso Sync replica."""

    def __init__(
        self,
        database_path: str | Path,
        remote_url: str,
        auth_token: str | None,
        *,
        require_marker: bool = True,
    ) -> None:
        self.database_path: Path = Path(database_path).expanduser().resolve()
        self.remote_url: str = remote_url
        self.__auth_token: str | None = auth_token
        self.__require_marker: bool = require_marker
        self.__connection: SyncConnection | None = None
        self.__file_lock: SyncFileLock | None = None
        self.__initialization_lock: RLock = RLock()
        self.__operation_lock: LockType | None = None

    @contextmanager
    def connection(self) -> Iterator[SyncConnection]:
        connection: SyncConnection = self._get_connection()
        operation_lock: LockType | None = self.__operation_lock
        if operation_lock is None:
            raise DatabaseException(
                'The local Turso Sync process lock is unavailable.',
            )
        operation_lock.acquire()
        try:
            yield connection
        finally:
            operation_lock.release()

    @contextmanager
    def transaction(self) -> Iterator[SyncConnection]:
        with self.connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def verify_tables(self, required_tables: set[str]) -> None:
        with self.connection() as connection:
            rows = connection.execute(
                '''
                SELECT name
                FROM sqlite_schema
                WHERE type = 'table'
                ''',
            ).fetchall()
        available_tables: set[str] = {str(row['name']) for row in rows}
        missing_tables: set[str] = required_tables - available_tables
        if missing_tables:
            raise DatabaseConfigurationError(
                'The synchronized database schema is incomplete; '
                'run the Turso schema setup and local migration.',
            )

    def pull(self) -> bool:
        with self.connection() as connection:
            try:
                return bool(connection.pull())
            except Exception as e:
                raise DatabaseSyncError(
                    'Turso pull failed; local data remains available.',
                ) from e

    def push(self) -> None:
        with self.connection() as connection:
            try:
                connection.push()
            except Exception as e:
                raise DatabaseSyncError(
                    'Turso push failed; local changes remain pending.',
                ) from e

    def stats(self) -> SyncStats:
        with self.connection() as connection:
            stats = connection.stats()
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

    def mark_sync_managed(self) -> None:
        marker: Path = sync_marker_path(self.database_path)
        marker.parent.mkdir(parents=True, exist_ok=True)
        temporary_marker: Path = marker.with_suffix(
            f'{marker.suffix}.tmp',
        )
        try:
            temporary_marker.write_text(
                _SYNC_MARKER_CONTENT,
                encoding='ascii',
            )
            os.replace(temporary_marker, marker)
        except OSError as e:
            raise DatabaseException(
                'Could not mark the local database as Turso Sync managed.',
            ) from e

    def close(self) -> None:
        with self.__initialization_lock:
            connection: SyncConnection | None = self.__connection
            file_lock: SyncFileLock | None = self.__file_lock
            self.__connection = None
            self.__file_lock = None
            self.__operation_lock = None

        try:
            if connection is not None:
                connection.close()
        finally:
            if file_lock is not None:
                file_lock.release()

    def _get_connection(self) -> SyncConnection:
        with self.__initialization_lock:
            if self.__connection is not None:
                return self.__connection
            marker: Path = sync_marker_path(self.database_path)
            if self.__require_marker and not marker.is_file():
                raise DatabaseConfigurationError(
                    'The local file is not marked as a Turso Sync replica; '
                    'run the local migration command first.',
                )

            file_lock: SyncFileLock = acquire_sync_file_lock(
                self.database_path,
            )
            try:
                connection: SyncConnection = open_turso_sync_connection(
                    self.database_path,
                    self.remote_url,
                    self.__auth_token,
                )
            except BaseException:
                file_lock.release()
                raise

            self.__connection = connection
            self.__file_lock = file_lock
            self.__operation_lock = file_lock.operation_lock
            return connection


__all__: list[str] = [
    'SyncConnection',
    'SyncFileLock',
    'SyncStats',
    'TursoSyncDatabase',
    'acquire_sync_file_lock',
    'open_turso_sync_connection',
    'sync_marker_path',
    'validate_sync_url',
]
