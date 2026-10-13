import json
import sqlite3
import time
from typing import Any

from finance.services.report_store.database import (
    SQLiteReportDatabase,
    cache_database,
)


class SQLiteCache:
    def __init__(
        self,
        database: SQLiteReportDatabase = cache_database,
    ) -> None:
        self.__database: SQLiteReportDatabase = database

    def get(
        self,
        namespace: str,
        cache_key: str,
        *,
        now: int | None = None,
    ) -> bytes | None:
        self.__database.initialize()
        checked_at: int = now if now is not None else int(time.time())
        with self.__database.connection() as connection:
            row: sqlite3.Row | None = connection.execute(
                '''
                SELECT value, expires_at
                FROM cache_entries
                WHERE namespace = ? AND cache_key = ?
                LIMIT 1
                ''',
                (namespace, cache_key),
            ).fetchone()
        if row is None:
            return None
        if int(row['expires_at']) <= checked_at:
            with self.__database.transaction() as connection:
                connection.execute(
                    '''
                    DELETE FROM cache_entries
                    WHERE namespace = ? AND cache_key = ? AND expires_at <= ?
                    ''',
                    (namespace, cache_key, checked_at),
                )
            return None
        value: bytes = bytes(row['value'])
        return value

    def set(
        self,
        namespace: str,
        cache_key: str,
        value: bytes,
        *,
        ttl_seconds: int,
        metadata: dict[str, Any] | None = None,
        now: int | None = None,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError('Cache TTL must be positive')
        if not isinstance(value, bytes):
            raise TypeError('Cache values must be bytes')

        self.__database.initialize()
        created_at: int = now if now is not None else int(time.time())
        metadata_json: str = json.dumps(
            metadata or {},
            ensure_ascii=False,
            separators=(',', ':'),
            sort_keys=True,
        )
        with self.__database.transaction() as connection:
            connection.execute(
                'DELETE FROM cache_entries WHERE expires_at <= ?',
                (created_at,),
            )
            connection.execute(
                '''
                INSERT INTO cache_entries (
                    namespace, cache_key, value, metadata_json,
                    created_at, expires_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(namespace, cache_key) DO UPDATE SET
                    value = excluded.value,
                    metadata_json = excluded.metadata_json,
                    created_at = excluded.created_at,
                    expires_at = excluded.expires_at
                ''',
                (
                    namespace,
                    cache_key,
                    sqlite3.Binary(value),
                    metadata_json,
                    created_at,
                    created_at + ttl_seconds,
                ),
            )

    def delete(self, namespace: str, cache_key: str) -> bool:
        self.__database.initialize()
        with self.__database.transaction() as connection:
            result = connection.execute(
                '''
                DELETE FROM cache_entries
                WHERE namespace = ? AND cache_key = ?
                ''',
                (namespace, cache_key),
            )
        return result.rowcount > 0

    def cleanup_expired(self, *, now: int | None = None) -> int:
        self.__database.initialize()
        cleanup_at: int = now if now is not None else int(time.time())
        with self.__database.transaction() as connection:
            result = connection.execute(
                'DELETE FROM cache_entries WHERE expires_at <= ?',
                (cleanup_at,),
            )
        self.__database.incremental_vacuum()
        return result.rowcount


cache: SQLiteCache = SQLiteCache()
