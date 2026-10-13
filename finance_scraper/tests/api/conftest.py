 
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from finance.config import DEFAULT_LANGUAGE
from finance.services.account.models import Account
from finance.services.account.exceptions import (
    AccountAlreadyExistsError as FinanceAccountAlreadyExistsError,
)
from finance.types.language import Language

import api.core.main as api_main
import api.core.database as api_database
import api.core.security as api_security
import api.repositories.report as report_repository
import api.routers.accounts as accounts_router
import api.routers.auth as auth_router
import api.services.report_migration as report_migration
import api.services.report_worker as report_worker
import finance.services.reporter.repository as reporter_repository
import finance.services.account.db as account_database
from finance.services.database import get_database_pool
from finance.services.database.repository import create_schema
from finance.services.report_store.cache import SQLiteCache
from finance.services.report_store.database import (
    SQLiteReportDatabase,
    create_report_schema,
)
from finance.services.report_store import reports as ReportStore
from api.core.config import APIConfig, settings
from api.services.rate_limit import limiter
from api.main import app


@pytest.fixture
def api_test_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    account_database_path: Path = tmp_path / 'accounts.sqlite3'
    temporary_settings: APIConfig = APIConfig(
        api=settings.api.model_copy(
            update={
                'database_path': tmp_path / 'api.sqlite3',
            },
        ),
    )
    monkeypatch.setattr(api_database, 'settings', temporary_settings)
    monkeypatch.setattr(report_repository, 'settings', temporary_settings)
    monkeypatch.setattr(report_migration, 'settings', temporary_settings)
    monkeypatch.setattr(account_database, 'DATABASE_PATH', account_database_path)

    async def get_test_account_pool():
        pool = await get_database_pool(account_database_path)
        async with pool.transaction() as connection:
            await create_schema(connection)
            await account_database.create_account_schema(connection)
        return pool

    async def get_test_sync_pool(
        database: str | Path,
        **options: Any,
    ):
        return await get_database_pool(
            account_database_path,
            size=options.get('size', 2),
            acquire_timeout=options.get('acquire_timeout', 5.0),
        )

    async def wait_for_shutdown(
        pool: Any,
        stop_event: Any,
    ) -> None:
        await stop_event.wait()

    monkeypatch.setattr(account_database, '_pool', get_test_account_pool)
    monkeypatch.setattr(api_main, 'get_turso_sync_pool', get_test_sync_pool)
    monkeypatch.setattr(api_main, 'run_sync_worker', wait_for_shutdown)

    test_report_database: SQLiteReportDatabase = SQLiteReportDatabase(
        tmp_path / 'report_store.sqlite3',
    )
    with test_report_database.connection() as connection:
        create_report_schema(connection)
    monkeypatch.setattr(ReportStore, 'report_database', test_report_database)
    monkeypatch.setattr(api_main, 'report_database', test_report_database)

    test_cache: SQLiteCache = SQLiteCache(
        SQLiteReportDatabase(tmp_path / 'cache.sqlite3'),
    )
    monkeypatch.setattr(report_worker, 'shared_cache', test_cache)
    monkeypatch.setattr(reporter_repository, 'report_cache', test_cache)

    return tmp_path


@pytest.fixture
def api_client(
    api_test_paths: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, dict[str, Any]]]:
    accounts: dict[str, Account] = {}
    passwords: dict[str, str] = {}

    def add_account(
        name: str,
        email: str,
        password: str,
        role: str = 'user',
    ) -> Account:
        account: Account = Account(
            id=uuid4(),
            name=name,
            email=email,
            role=role,
            language=Language(**DEFAULT_LANGUAGE),
        )
        account = account.model_copy(update={'account_id': account.id})
        accounts[str(account.id)] = account
        passwords[str(account.email).casefold()] = password
        return account

    admin: Account = add_account(
        'Test Admin',
        'admin@example.com',
        'admin-password',
        role='admin',
    )
    add_account(
        'Test User',
        'user@example.com',
        'user-password',
    )

    async def authenticate(email: str, password: str) -> Account | None:
        account_id: str | None = next(
            (
                identifier
                for identifier, account in accounts.items()
                if str(account.email).casefold() == email.casefold()
            ),
            None,
        )
        if (
            account_id is None
            or passwords.get(email.casefold()) != password
        ):
            return None
        return accounts[account_id]

    async def get_by_id(account_id: str) -> Account | None:
        return accounts.get(str(account_id))

    async def list_accounts() -> list[Account]:
        return list(accounts.values())

    async def get_account(account_id: Any) -> Account | None:
        return accounts.get(str(account_id))

    async def create_account(payload: Any) -> Account:
        email: str = str(payload.email)
        if any(
            str(account.email).casefold() == email.casefold()
            for account in accounts.values()
        ):
            raise FinanceAccountAlreadyExistsError(email)
        account: Account = Account(
            id=uuid4(),
            name=payload.name,
            email=payload.email,
            role='user',
            language=payload.language or Language(**DEFAULT_LANGUAGE),
            custom_report=payload.custom_report,
            watchlist=payload.watchlist,
            portfolio=payload.portfolio,
        )
        account = account.model_copy(update={'account_id': account.id})
        accounts[str(account.id)] = account
        passwords[email.casefold()] = payload.password.get_secret_value()
        return account

    async def update_account(account: Account, payload: Any) -> Account:
        new_email: str = str(payload.email)
        duplicate_exists: bool = any(
            str(other.email).casefold() == new_email.casefold()
            and other.id != account.id
            for other in accounts.values()
        )
        if duplicate_exists:
            raise FinanceAccountAlreadyExistsError(new_email)
        updated: Account = account.model_copy(
            update={
                'name': payload.name,
                'email': payload.email,
                'language': payload.language or account.language,
                'custom_report': (
                    payload.custom_report
                    if payload.custom_report is not None
                    else account.custom_report
                ),
                'watchlist': (
                    payload.watchlist
                    if payload.watchlist is not None
                    else account.watchlist
                ),
                'portfolio': (
                    payload.portfolio
                    if payload.portfolio is not None
                    else account.portfolio
                ),
            },
        )
        accounts.pop(str(account.id))
        accounts[str(updated.id)] = updated
        password: str = passwords.pop(str(account.email).casefold())
        passwords[new_email.casefold()] = password
        return updated

    async def delete_account(account_id: Any) -> Account | None:
        account: Account | None = accounts.pop(str(account_id), None)
        if account is not None:
            passwords.pop(str(account.email).casefold(), None)
        return account

    async def change_password(
        account_id: Any,
        current_password: str,
        new_password: str,
    ) -> bool:
        account: Account | None = accounts.get(str(account_id))
        if account is None:
            return False
        email: str = str(account.email).casefold()
        if passwords.get(email) != current_password:
            return False
        passwords[email] = new_password
        return True

    monkeypatch.setattr(auth_router, 'authenticate', authenticate)
    monkeypatch.setattr(api_security, 'get_by_id', get_by_id)
    monkeypatch.setattr(accounts_router.AccountRepository, 'list_accounts', list_accounts)
    monkeypatch.setattr(accounts_router.AccountRepository, 'get_account', get_account)
    monkeypatch.setattr(accounts_router.AccountRepository, 'create_account', create_account)
    monkeypatch.setattr(accounts_router.AccountRepository, 'update_account', update_account)
    monkeypatch.setattr(accounts_router.AccountRepository, 'delete_account', delete_account)
    monkeypatch.setattr(accounts_router.AccountRepository, 'change_password', change_password)
    limiter.reset()

    state: dict[str, Any] = {
        'accounts': accounts,
        'passwords': passwords,
        'admin': admin,
    }
    with TestClient(app) as client:
        yield client, state
