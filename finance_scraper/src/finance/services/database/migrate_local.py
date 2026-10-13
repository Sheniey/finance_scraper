"""Seed a new Turso Sync replica from the existing local SQLite databases."""

import logging
import hashlib
import os
import sqlite3
import time
from collections.abc import Mapping, Sequence
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from finance.config import DB_AUTH_TOKEN, DB_LOCAL_PATH, DB_LOCATION, MODULE_ROOT
from finance.services.database.exceptions import (
    DatabaseConfigurationError,
    DatabaseException,
)
from finance.services.database.sync import (
    SyncConnection,
    TursoSyncDatabase,
    sync_marker_path,
)


logger: logging.Logger = logging.getLogger(__name__)
_MIGRATION_ID: str = 'local-data-seed-v1'
_ACCOUNT_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    'languages': ('code', 'name'),
    'tickers': ('ticker_id', 'ticker', 'region'),
    'currencies': ('currency_id', 'currency'),
    'accounts': (
        'account_id',
        'email',
        'name',
        'role',
        'language_code',
        'language_style',
        'password_hash',
    ),
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
_REPORT_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    'report_jobs': (
        'report_id',
        'account_id',
        'resource',
        'request_json',
        'status',
        'filename',
        'report_format',
        'content_type',
        'metadata_json',
        'artifact',
        'cache_key',
        'is_personalized',
        'source',
        'error_code',
        'created_at',
        'updated_at',
        'started_at',
        'completed_at',
        'expires_at',
        'worker_id',
        'lease_until',
    ),
    'report_store_migrations': (
        'source_database',
        'completed_at',
    ),
}
_MIGRATION_SOURCE: str = f'finance-scraper:{_MIGRATION_ID}'


def _source_directory() -> Path:
    configured_directory: str = os.getenv(
        'LEGACY_DATABASE_DIR',
        str(MODULE_ROOT / 'db'),
    )
    return Path(configured_directory).expanduser().resolve()


def _readonly_connection(database_path: Path) -> sqlite3.Connection:
    readonly_uri: str = f'{database_path.resolve().as_uri()}?mode=ro'
    connection: sqlite3.Connection = sqlite3.connect(
        readonly_uri,
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA query_only = ON')
    return connection


def _backup_source(database_path: Path) -> Path:
    timestamp: str = datetime.now(timezone.utc).strftime(
        '%Y%m%dT%H%M%S%fZ',
    )
    backup_path: Path = database_path.with_name(
        f'{database_path.name}-pre-sync-{timestamp}',
    )
    with closing(_readonly_connection(database_path)) as source:
        with closing(sqlite3.connect(backup_path)) as backup:
            source.backup(backup)
    logger.info('Created local migration backup: %s', backup_path.name)
    return backup_path


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row: sqlite3.Row | None = connection.execute(
        '''
        SELECT 1
        FROM sqlite_schema
        WHERE type = 'table' AND name = ?
        LIMIT 1
        ''',
        (table_name,),
    ).fetchone()
    return row is not None


def _validate_source_schema(
    database_path: Path,
    required_tables: Mapping[str, tuple[str, ...]],
) -> None:
    with closing(_readonly_connection(database_path)) as connection:
        for table_name, expected_columns in required_tables.items():
            if not _table_exists(connection, table_name):
                raise DatabaseConfigurationError(
                    f'The local source is missing required table {table_name!r}.',
                )

            actual_columns: tuple[str, ...] = tuple(
                str(row['name'])
                for row in connection.execute(
                    f'PRAGMA table_info({table_name})',
                ).fetchall()
            )
            if set(actual_columns) != set(expected_columns):
                raise DatabaseConfigurationError(
                    f'The local source schema for {table_name!r} is not supported.',
                )

        account_id_type: str | None = next(
            (
                str(row['type']).upper()
                for row in connection.execute(
                    'PRAGMA table_info(accounts)',
                ).fetchall()
                if row['name'] == 'account_id'
            ),
            None,
        )
        if account_id_type != 'TEXT':
            raise DatabaseConfigurationError(
                'The local account source must use TEXT UUID account IDs; '
                'migrate it before bootstrapping Turso Sync.',
            )


def _copy_table(
    source_path: Path,
    target: SyncConnection,
    table_name: str,
    columns: tuple[str, ...],
) -> int:
    with closing(_readonly_connection(source_path)) as source:
        if not _table_exists(source, table_name):
            return 0

        placeholders: str = ', '.join('?' for _ in columns)
        column_sql: str = ', '.join(columns)
        statement: str = (
            f'INSERT INTO {table_name} ({column_sql}) '
            f'VALUES ({placeholders})'
        )
        rows = source.execute(
            f'SELECT {column_sql} FROM {table_name}',
        )
        copied_rows: int = 0
        for row in rows:
            target.execute(
                statement,
                tuple(row[column] for column in columns),
            )
            copied_rows += 1
    return copied_rows


def _row_digest(values: Sequence[object]) -> bytes:
    row_hash: Any = hashlib.sha256()
    for value in values:
        if value is None:
            row_hash.update(b'n')
        elif isinstance(value, bool):
            row_hash.update(b'i')
            row_hash.update(str(int(value)).encode('ascii'))
        elif isinstance(value, int):
            row_hash.update(b'i')
            row_hash.update(str(value).encode('ascii'))
        elif isinstance(value, float):
            row_hash.update(b'f')
            row_hash.update(value.hex().encode('ascii'))
        elif isinstance(value, str):
            encoded_value: bytes = value.encode('utf-8')
            row_hash.update(b's')
            row_hash.update(len(encoded_value).to_bytes(8, 'big'))
            row_hash.update(encoded_value)
        elif isinstance(value, (bytes, bytearray, memoryview)):
            encoded_value = bytes(value)
            row_hash.update(b'b')
            row_hash.update(len(encoded_value).to_bytes(8, 'big'))
            row_hash.update(encoded_value)
        else:
            raise DatabaseException(
                'A source database contains an unsupported SQLite value type.',
            )
    return row_hash.digest()


def _digest_table(
    connection: SyncConnection,
    table_name: str,
    columns: tuple[str, ...],
    *,
    where_clause: str = '',
    parameters: tuple[object, ...] = (),
) -> tuple[int, bytes]:
    column_sql: str = ', '.join(columns)
    query: str = f'SELECT {column_sql} FROM {table_name} {where_clause}'
    table_hash: Any = hashlib.sha256()
    row_digests: list[bytes] = []
    row_count: int = 0
    for row in connection.execute(query, parameters):
        row_digests.append(_row_digest(row))
        row_count += 1
    for digest in sorted(row_digests):
        table_hash.update(digest)
    return row_count, table_hash.digest()


def _source_table_digest(
    database_path: Path,
    table_name: str,
    columns: tuple[str, ...],
) -> tuple[int, bytes]:
    with closing(_readonly_connection(database_path)) as connection:
        if not _table_exists(connection, table_name):
            return 0, hashlib.sha256().digest()
        return _digest_table(
            connection,
            table_name,
            columns,
        )


def _target_row_count(connection: SyncConnection, table_name: str) -> int:
    row = connection.execute(
        f'SELECT COUNT(*) AS row_count FROM {table_name}',
    ).fetchone()
    if row is None:
        raise DatabaseException(
            f'Could not count rows in the synchronized table {table_name!r}.',
        )
    return int(row['row_count'])


def _write_migration_state(state_path: Path) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path = state_path.with_suffix(
        f'{state_path.suffix}.tmp',
    )
    try:
        temporary_path.write_text(_MIGRATION_ID, encoding='ascii')
        os.replace(temporary_path, state_path)
    except OSError as e:
        raise DatabaseException(
            'Could not record the local Turso Sync migration state.',
        ) from e


def migrate_local_data() -> None:
    """Back up and seed the sync replica from local account/report files."""

    source_directory: Path = _source_directory()
    account_source: Path = source_directory / 'financescraper.sqlite3'
    report_source: Path = source_directory / 'report_store.sqlite3'
    if not account_source.is_file():
        raise DatabaseConfigurationError(
            'The local financescraper.sqlite3 source file was not found.',
        )
    if not report_source.is_file():
        raise DatabaseConfigurationError(
            'The local report_store.sqlite3 source file was not found.',
        )

    _validate_source_schema(account_source, _ACCOUNT_TABLE_COLUMNS)
    if report_source.exists():
        with closing(_readonly_connection(report_source)) as report_connection:
            for table_name, expected_columns in _REPORT_TABLE_COLUMNS.items():
                if not _table_exists(report_connection, table_name):
                    continue
                actual_columns: set[str] = {
                    str(row['name'])
                    for row in report_connection.execute(
                        f'PRAGMA table_info({table_name})',
                    ).fetchall()
                }
                if actual_columns != set(expected_columns):
                    raise DatabaseConfigurationError(
                        f'The local source schema for {table_name!r} is not supported.',
                    )

    target_path: Path = Path(DB_LOCAL_PATH).expanduser().resolve()
    managed_marker: Path = sync_marker_path(target_path)
    migration_state_path: Path = Path(
        f'{target_path}.migration-in-progress',
    )
    target_exists: bool = target_path.exists()
    can_resume_migration: bool = migration_state_path.is_file()
    if target_exists and not managed_marker.is_file() and not can_resume_migration:
        raise DatabaseConfigurationError(
            'The target file already exists but is not marked as a Turso Sync '
            'replica; it will not be opened or overwritten.',
        )
    if managed_marker.is_file() and not target_exists:
        raise DatabaseConfigurationError(
            'The Turso Sync marker exists but the local database file is missing.',
        )

    _backup_source(account_source)
    _backup_source(report_source)
    if not managed_marker.is_file():
        _write_migration_state(migration_state_path)

    target: TursoSyncDatabase = TursoSyncDatabase(
        target_path,
        DB_LOCATION,
        DB_AUTH_TOKEN,
        require_marker=managed_marker.is_file(),
    )
    try:
        target.pull()
        target.verify_tables(
            {*_ACCOUNT_TABLE_COLUMNS, *_REPORT_TABLE_COLUMNS},
        )

        migration_exists: bool = False
        with target.connection() as connection:
            migration_exists = (
                connection.execute(
                    '''
                    SELECT 1
                    FROM report_store_migrations
                    WHERE source_database = ?
                    LIMIT 1
                    ''',
                    (_MIGRATION_SOURCE,),
                ).fetchone()
                is not None
            )

        if not migration_exists:
            for table_name in (*_ACCOUNT_TABLE_COLUMNS, *_REPORT_TABLE_COLUMNS):
                with target.connection() as connection:
                    if _target_row_count(connection, table_name) != 0:
                        raise DatabaseConfigurationError(
                            'The new Turso database is not empty and has no '
                            'matching local migration marker; refusing to merge.',
                        )

            copied_counts: dict[str, int] = {}
            with target.transaction() as connection:
                for table_name, columns in _ACCOUNT_TABLE_COLUMNS.items():
                    copied_counts[table_name] = _copy_table(
                        account_source,
                        connection,
                        table_name,
                        columns,
                    )
                for table_name, columns in _REPORT_TABLE_COLUMNS.items():
                    copied_counts[table_name] = _copy_table(
                        report_source,
                        connection,
                        table_name,
                        columns,
                    )
                copied_counts['report_store_migrations'] += 1
                connection.execute(
                    '''
                    INSERT INTO report_store_migrations (
                        source_database, completed_at
                    )
                    VALUES (?, ?)
                    ''',
                    (_MIGRATION_SOURCE, int(time.time())),
                )

            for table_name, columns in (
                *_ACCOUNT_TABLE_COLUMNS.items(),
                *(
                    (name, column_names)
                    for name, column_names in _REPORT_TABLE_COLUMNS.items()
                    if name != 'report_store_migrations'
                ),
            ):
                source_path: Path = (
                    account_source
                    if table_name in _ACCOUNT_TABLE_COLUMNS
                    else report_source
                )
                expected_count, expected_digest = _source_table_digest(
                    source_path,
                    table_name,
                    columns,
                )
                with target.connection() as connection:
                    actual_count, actual_digest = _digest_table(
                        connection,
                        table_name,
                        columns,
                    )
                if (
                    expected_count != copied_counts[table_name]
                    or actual_count != expected_count
                    or actual_digest != expected_digest
                ):
                    raise DatabaseException(
                        f'Local migration verification failed for {table_name!r}.',
                    )

            expected_count, expected_digest = _source_table_digest(
                report_source,
                'report_store_migrations',
                _REPORT_TABLE_COLUMNS['report_store_migrations'],
            )
            with target.connection() as connection:
                actual_count, actual_digest = _digest_table(
                    connection,
                    'report_store_migrations',
                    _REPORT_TABLE_COLUMNS['report_store_migrations'],
                    where_clause='WHERE source_database != ?',
                    parameters=(_MIGRATION_SOURCE,),
                )
                foreign_key_violations = connection.execute(
                    'PRAGMA foreign_key_check',
                ).fetchall()
                migration_marker_exists: bool = (
                    connection.execute(
                        '''
                        SELECT 1
                        FROM report_store_migrations
                        WHERE source_database = ?
                        LIMIT 1
                        ''',
                        (_MIGRATION_SOURCE,),
                    ).fetchone()
                    is not None
                )
                total_migration_count: int = _target_row_count(
                    connection,
                    'report_store_migrations',
                )
            if (
                actual_count != expected_count
                or actual_digest != expected_digest
                or not migration_marker_exists
                or total_migration_count != expected_count + 1
                or foreign_key_violations
            ):
                raise DatabaseException(
                    'Local migration verification failed for shared metadata '
                    'or foreign-key integrity.',
                )

        target.push()
        stats = target.stats()
        if stats.cdc_operations != 0:
            raise DatabaseException(
                'Turso accepted the push but local CDC still reports pending operations.',
            )

        target.mark_sync_managed()
        if migration_state_path.exists():
            migration_state_path.unlink()
        logger.info(
            'Local accounts, shared tables, and report jobs were synchronized.',
        )
    finally:
        target.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    migrate_local_data()


if __name__ == '__main__':
    main()
