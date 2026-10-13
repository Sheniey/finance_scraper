import sqlite3
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import finance.services.database.migrate_local as local_migration
from finance.services.database.sync import sync_marker_path


class FakeTursoSyncDatabase:
    def __init__(
        self,
        database_path: str | Path,
        remote_url: str,
        auth_token: str | None,
        *,
        require_marker: bool,
    ) -> None:
        self.database_path: Path = Path(database_path)
        self.connection_handle: sqlite3.Connection = sqlite3.connect(
            self.database_path,
            isolation_level=None,
        )
        self.connection_handle.row_factory = sqlite3.Row
        self.connection_handle.execute('PRAGMA foreign_keys = ON')
        schema_path: Path = (
            Path(__file__).parents[1]
            / 'src'
            / 'finance'
            / 'services'
            / 'database'
            / 'schema.sql'
        )
        self.connection_handle.executescript(
            schema_path.read_text(encoding='utf-8'),
        )

    def pull(self) -> bool:
        return False

    def verify_tables(self, required_tables: set[str]) -> None:
        rows = self.connection_handle.execute(
            "SELECT name FROM sqlite_schema WHERE type = 'table'",
        ).fetchall()
        existing_tables: set[str] = {str(row['name']) for row in rows}
        assert required_tables.issubset(existing_tables)

    @contextmanager
    def connection(self):
        yield self.connection_handle

    @contextmanager
    def transaction(self):
        self.connection_handle.execute('BEGIN IMMEDIATE')
        try:
            yield self.connection_handle
            self.connection_handle.commit()
        except BaseException:
            self.connection_handle.rollback()
            raise

    def push(self) -> None:
        return None

    def stats(self) -> SimpleNamespace:
        return SimpleNamespace(cdc_operations=0)

    def mark_sync_managed(self) -> None:
        sync_marker_path(self.database_path).write_text(
            'turso-sync-v1\n',
            encoding='ascii',
        )

    def close(self) -> None:
        self.connection_handle.close()


def _create_database(database_path: Path) -> sqlite3.Connection:
    schema_path: Path = (
        Path(__file__).parents[1]
        / 'src'
        / 'finance'
        / 'services'
        / 'database'
        / 'schema.sql'
    )
    connection: sqlite3.Connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    connection.executescript(schema_path.read_text(encoding='utf-8'))
    return connection


def test_local_migration_preserves_accounts_and_reports_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_directory: Path = tmp_path / 'legacy'
    source_directory.mkdir()
    account_source: Path = source_directory / 'financescraper.sqlite3'
    report_source: Path = source_directory / 'report_store.sqlite3'
    target_path: Path = tmp_path / 'sync' / 'financescraper.sqlite3'

    with _create_database(account_source) as connection:
        connection.execute(
            'INSERT INTO languages (code, name) VALUES (?, ?)',
            ('en', 'English'),
        )
        connection.execute(
            'INSERT INTO tickers (ticker_id, ticker, region) VALUES (?, ?, ?)',
            (1, 'AAPL', 'US'),
        )
        connection.execute(
            'INSERT INTO currencies (currency_id, currency) VALUES (?, ?)',
            (1, 'USD'),
        )
        connection.execute(
            '''
            INSERT INTO accounts (
                account_id, email, name, language_code, language_style,
                password_hash
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            ('account-uuid', 'owner@example.test', 'Owner', 'en', 'friendly', 'hash'),
        )
        connection.execute(
            '''
            INSERT INTO action_history (
                action_id, account_id, ticker_id, currency_id, action,
                quantity, price, timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (10, 'account-uuid', 1, 1, 'BUY', 2, 50.5, '2026-01-01'),
        )
        connection.execute(
            '''
            CREATE TABLE api_tokens (
                token_id TEXT PRIMARY KEY,
                token TEXT NOT NULL
            )
            ''',
        )
        connection.execute(
            'INSERT INTO api_tokens (token_id, token) VALUES (?, ?)',
            ('local-only-token', 'secret'),
        )

    with _create_database(report_source) as connection:
        connection.execute(
            '''
            INSERT INTO report_jobs (
                report_id, account_id, resource, request_json, status,
                filename, report_format, content_type, artifact, created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                'rep_local',
                'account-uuid',
                'AAPL.US',
                '{"ticker":"AAPL.US"}',
                'COMPLETED',
                'report.pdf',
                'pdf',
                'application/pdf',
                sqlite3.Binary(b'pdf-report'),
                100,
                101,
            ),
        )
        connection.execute(
            '''
            CREATE TABLE cache_entries (
                cache_key TEXT PRIMARY KEY,
                value BLOB NOT NULL
            )
            ''',
        )
        connection.execute(
            'INSERT INTO cache_entries (cache_key, value) VALUES (?, ?)',
            ('cache-only', sqlite3.Binary(b'cache-value')),
        )

    monkeypatch.setenv('LEGACY_DATABASE_DIR', str(source_directory))
    monkeypatch.setattr(local_migration, 'DB_LOCAL_PATH', target_path)
    monkeypatch.setattr(
        local_migration,
        'DB_LOCATION',
        'turso://financescraper.example.test',
    )
    monkeypatch.setattr(local_migration, 'DB_AUTH_TOKEN', 'test-token')
    monkeypatch.setattr(
        local_migration,
        'TursoSyncDatabase',
        FakeTursoSyncDatabase,
    )

    local_migration.migrate_local_data()

    with sqlite3.connect(target_path) as connection:
        connection.row_factory = sqlite3.Row
        account = connection.execute(
            'SELECT account_id, email FROM accounts',
        ).fetchone()
        action = connection.execute(
            'SELECT account_id, price FROM action_history',
        ).fetchone()
        report = connection.execute(
            'SELECT report_id, artifact FROM report_jobs',
        ).fetchone()
        target_tables: set[str] = {
            str(row['name'])
            for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type = 'table'",
            ).fetchall()
        }

    assert account['account_id'] == 'account-uuid'
    assert account['email'] == 'owner@example.test'
    assert action['account_id'] == 'account-uuid'
    assert action['price'] == 50.5
    assert report['report_id'] == 'rep_local'
    assert report['artifact'] == b'pdf-report'
    assert 'cache_entries' not in target_tables
    assert 'api_tokens' not in target_tables
    assert sync_marker_path(target_path).is_file()


def test_row_digest_is_order_independent_and_checks_blob_values() -> None:
    first_digest: bytes = local_migration._row_digest(
        ('report.pdf', b'first', None),
    )
    second_digest: bytes = local_migration._row_digest(
        ('report.pdf', b'second', None),
    )

    assert first_digest != second_digest
