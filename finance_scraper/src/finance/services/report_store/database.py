from collections.abc import Iterator
from contextlib import contextmanager
import logging
from pathlib import Path
from threading import RLock
import sqlite3

from finance.config import (
    DB_AUTH_TOKEN,
    DB_LOCAL_PATH,
    DB_LOCATION,
    DESKTOP_LOCAL_ONLY,
    REPORT_STORE_PATH,
)
from finance.services.database.exceptions import DatabaseSyncError
from finance.services.database.sync import (
    SyncConnection,
    TursoSyncDatabase,
)


logger: logging.Logger = logging.getLogger(__name__)
REPORT_SCHEMA_STATEMENTS: tuple[str, ...] = (
    '''
    CREATE TABLE IF NOT EXISTS report_jobs (
        report_id TEXT PRIMARY KEY,
        account_id TEXT NOT NULL,
        resource TEXT NOT NULL,
        request_json TEXT NOT NULL,
        status TEXT NOT NULL CHECK (
            status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED')
        ),
        filename TEXT NOT NULL,
        report_format TEXT NOT NULL,
        content_type TEXT NOT NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        artifact BLOB,
        cache_key TEXT,
        is_personalized INTEGER NOT NULL DEFAULT 0 CHECK (
            is_personalized IN (0, 1)
        ),
        source TEXT NOT NULL DEFAULT 'api',
        error_code TEXT,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        started_at INTEGER,
        completed_at INTEGER,
        expires_at INTEGER,
        worker_id TEXT,
        lease_until INTEGER,
        CHECK (status != 'COMPLETED' OR artifact IS NOT NULL)
    )
    ''',
    '''
    CREATE INDEX IF NOT EXISTS idx_report_jobs_queue
    ON report_jobs (status, lease_until, created_at)
    ''',
    '''
    CREATE INDEX IF NOT EXISTS idx_report_jobs_owner
    ON report_jobs (account_id, created_at)
    ''',
    '''
    CREATE INDEX IF NOT EXISTS idx_report_jobs_expiry
    ON report_jobs (expires_at, status)
    ''',
    '''
    CREATE TABLE IF NOT EXISTS report_store_migrations (
        source_database TEXT PRIMARY KEY,
        completed_at INTEGER NOT NULL
    )
    ''',
)


def create_report_schema(connection: SyncConnection) -> None:
    """Create report tables for isolated tests and migration tooling."""

    for statement in REPORT_SCHEMA_STATEMENTS:
        connection.execute(statement)


class SQLiteReportDatabase:
    """Persist local report cache entries in a standalone SQLite file."""

    def __init__(self, database_path: Path = REPORT_STORE_PATH) -> None:
        self.database_path: Path = database_path
        self.__initialization_lock: RLock = RLock()
        self.__initialized_path: Path | None = None

    def _open_connection(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection: sqlite3.Connection = sqlite3.connect(
            self.database_path,
            timeout=30,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA busy_timeout = 30000')
        connection.execute('PRAGMA foreign_keys = ON')
        connection.execute('PRAGMA synchronous = NORMAL')
        return connection

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection: sqlite3.Connection = self._open_connection()
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def initialize(self) -> None:
        with self.__initialization_lock:
            resolved_path: Path = self.database_path.resolve()
            if self.__initialized_path == resolved_path:
                return

            is_new_database: bool = (
                not self.database_path.exists()
                or self.database_path.stat().st_size == 0
            )
            with self.connection() as connection:
                if is_new_database:
                    connection.execute('PRAGMA auto_vacuum = INCREMENTAL')
                connection.execute('PRAGMA journal_mode = WAL')
                connection.execute('PRAGMA synchronous = NORMAL')
                connection.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS cache_entries (
                        namespace TEXT NOT NULL,
                        cache_key TEXT NOT NULL,
                        value BLOB NOT NULL,
                        metadata_json TEXT NOT NULL DEFAULT '{}',
                        created_at INTEGER NOT NULL,
                        expires_at INTEGER NOT NULL,
                        PRIMARY KEY (namespace, cache_key)
                    )
                    ''',
                )
                connection.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS idx_cache_entries_expiry
                    ON cache_entries (expires_at)
                    ''',
                )
            self.__initialized_path = resolved_path

    def incremental_vacuum(self) -> None:
        self.initialize()
        with self.connection() as connection:
            connection.execute('PRAGMA incremental_vacuum')

    def checkpoint(self) -> None:
        self.initialize()
        with self.connection() as connection:
            connection.execute('PRAGMA wal_checkpoint(PASSIVE)')

    def close(self) -> None:
        """Close persistent resources; SQLite connections are request-scoped."""

        return None


class SQLiteReportStoreDatabase(SQLiteReportDatabase):
    """Persist report artifacts and cache entries in local SQLite."""

    def initialize(self) -> None:
        super().initialize()
        with self.connection() as connection:
            create_report_schema(connection)


class TursoSyncReportDatabase(TursoSyncDatabase):
    """Persist report jobs and artifacts in the local-first Turso replica."""

    def __init__(
        self,
        database_path: str | Path = DB_LOCAL_PATH,
        remote_url: str = DB_LOCATION,
        auth_token: str | None = DB_AUTH_TOKEN,
        *,
        require_marker: bool = True,
    ) -> None:
        super().__init__(
            database_path,
            remote_url,
            auth_token,
            require_marker=require_marker,
        )
        self.__initialized: bool = False
        self.__initialization_lock: RLock = RLock()

    def initialize(self) -> None:
        with self.__initialization_lock:
            if self.__initialized:
                return
            try:
                self.pull()
            except DatabaseSyncError as e:
                logger.warning(
                    'Initial report-store pull failed; checking the local replica: %s',
                    e,
                )
            self.verify_tables(
                {'report_jobs', 'report_store_migrations'},
            )
            self.__initialized = True

    def checkpoint(self) -> None:
        with self.connection() as connection:
            try:
                connection.checkpoint()
            except Exception as e:
                raise DatabaseSyncError(
                    'Could not checkpoint the local Turso Sync replica.',
                ) from e


cache_database: SQLiteReportDatabase = SQLiteReportDatabase()
report_database: SQLiteReportDatabase | TursoSyncReportDatabase = (
    TursoSyncReportDatabase()
    if DB_LOCATION and not DESKTOP_LOCAL_ONLY
    else SQLiteReportStoreDatabase(REPORT_STORE_PATH)
)
