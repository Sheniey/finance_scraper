import base64
import json
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from finance.config import DB_AUTH_TOKEN, DB_POOL_SIZE, DB_POOL_TIMEOUT
from finance.services.account import (
    Account,
    LLMProvider,
    SQLiteAccountRepository,
    change_password,
    get_account_llm_keys,
    get_account_llm_key_providers,
    regenerate_account_umk,
    set_account_llm_key
)
from finance.services.account import db as account_storage
from finance.services.account.exceptions import VaultLockedError
from finance.services.account.vault import (
    VaultAuthenticationError,
    VaultSessionCache,
    decrypt_provider_key,
    encrypt_provider_key,
    generate_umk,
    unwrap_umk,
    vault_sessions,
    wrap_umk
)
from finance.services.database import close_database_pools, get_database_pool


class VaultCryptographyTests(unittest.TestCase):
    def test_password_wrapped_umk_round_trips_and_rejects_wrong_context(self) -> None:
        account_id = uuid4()
        umk: bytes = generate_umk()
        envelope: str = wrap_umk(umk, 'account-password', account_id)

        self.assertEqual(len(umk), 32)
        self.assertEqual(
            unwrap_umk(envelope, 'account-password', account_id),
            umk,
        )
        self.assertNotIn(base64.b64encode(umk).decode('ascii'), envelope)
        with self.assertRaises(VaultAuthenticationError):
            unwrap_umk(envelope, 'incorrect-password', account_id)
        with self.assertRaises(VaultAuthenticationError):
            unwrap_umk(envelope, 'account-password', uuid4())

    def test_provider_key_ciphertext_is_bound_to_account_and_provider(self) -> None:
        account_id = uuid4()
        umk: bytes = generate_umk()
        api_key: str = 'sk-test-provider-key'
        envelope: str = encrypt_provider_key(
            api_key,
            umk,
            account_id,
            'openai',
        )

        self.assertEqual(
            decrypt_provider_key(
                envelope,
                umk,
                account_id,
                LLMProvider.CHATGPT,
            ),
            api_key,
        )
        self.assertNotIn(api_key, envelope)
        with self.assertRaises(VaultAuthenticationError):
            decrypt_provider_key(
                envelope,
                umk,
                account_id,
                LLMProvider.ANTHROPIC,
            )
        with self.assertRaises(VaultAuthenticationError):
            decrypt_provider_key(
                envelope,
                umk,
                uuid4(),
                LLMProvider.CHATGPT,
            )

    def test_vault_session_cache_is_scoped_and_lockable(self) -> None:
        cache: VaultSessionCache = VaultSessionCache()
        first_account_id = uuid4()
        second_account_id = uuid4()
        first_umk: bytes = generate_umk()

        cache.unlock(first_account_id, first_umk)

        self.assertEqual(cache.get(first_account_id), first_umk)
        self.assertIsNone(cache.get(second_account_id))
        cache.lock(first_account_id)
        self.assertIsNone(cache.get(first_account_id))


class AccountVaultRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._original_database_path = account_storage.DATABASE_PATH
        self._original_remote_url = account_storage.REMOTE_URL
        self._original_pool_factory = account_storage._pool
        self._directory = tempfile.TemporaryDirectory()
        self._database_path = Path(self._directory.name) / 'accounts.sqlite3'
        self._schema_key = str(self._database_path.resolve())
        account_storage.DATABASE_PATH = self._database_path
        account_storage.REMOTE_URL = ''
        account_storage._schema_ready.discard(self._schema_key)

        async def get_local_pool():
            return await get_database_pool(
                account_storage.DATABASE_PATH,
                auth_token=DB_AUTH_TOKEN,
                size=DB_POOL_SIZE,
                acquire_timeout=DB_POOL_TIMEOUT,
            )

        account_storage._pool = get_local_pool
        vault_sessions.clear()

    async def asyncTearDown(self) -> None:
        vault_sessions.clear()
        account_storage._schema_ready.discard(self._schema_key)
        account_storage.DATABASE_PATH = self._original_database_path
        account_storage.REMOTE_URL = self._original_remote_url
        account_storage._pool = self._original_pool_factory
        await close_database_pools()
        self._directory.cleanup()

    async def test_account_keys_are_encrypted_and_require_an_unlocked_umk(
        self,
    ) -> None:
        repository: SQLiteAccountRepository = SQLiteAccountRepository()
        account: Account = await repository.create(
            Account(
                name='Vault Owner',
                email='vault-owner@example.com',
            ),
            'account-password',
        )
        account_id = account.account_id or account.id

        pool = await get_database_pool(
            self._database_path,
            auth_token=DB_AUTH_TOKEN,
            size=DB_POOL_SIZE,
            acquire_timeout=DB_POOL_TIMEOUT,
        )
        async with pool.connection() as connection:
            row = (
                await connection.execute(
                    'SELECT encrypted_umk FROM accounts WHERE account_id = ?',
                    (str(account_id),),
                )
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertIsInstance(row['encrypted_umk'], str)
        self.assertNotIn('account-password', row['encrypted_umk'])

        authenticated_account = await repository.get_by_email(
            str(account.email),
            'account-password',
        )
        self.assertIsNotNone(authenticated_account)
        await set_account_llm_key(
            account_id,
            LLMProvider.DEEPSEEK,
            'sk-test-deepseek',
        )

        encrypted_keys = await account_storage.load_account_llm_key_envelopes(
            account_id,
        )
        self.assertNotIn('sk-test-deepseek', encrypted_keys['deepseek'])
        vault_sessions.lock(account_id)
        with self.assertRaises(VaultLockedError):
            await get_account_llm_keys(account_id)

        await repository.get_by_email(
            str(account.email),
            'account-password',
        )
        self.assertEqual(
            await get_account_llm_keys(account_id),
            {LLMProvider.DEEPSEEK: 'sk-test-deepseek'},
        )
        self.assertEqual(
            await get_account_llm_key_providers(account_id),
            [LLMProvider.DEEPSEEK],
        )

    async def test_password_change_rewraps_umk_and_preserves_provider_keys(
        self,
    ) -> None:
        repository: SQLiteAccountRepository = SQLiteAccountRepository()
        account: Account = await repository.create(
            Account(
                name='Password Owner',
                email='password-owner@example.com',
            ),
            'old-password',
        )
        account_id = account.account_id or account.id
        await repository.get_by_email(
            str(account.email),
            'old-password',
        )
        original_umk = vault_sessions.get(account_id)
        self.assertIsNotNone(original_umk)
        assert original_umk is not None
        await set_account_llm_key(
            account_id,
            LLMProvider.ANTHROPIC,
            'sk-test-anthropic',
        )

        self.assertTrue(
            await change_password(
                account_id,
                'old-password',
                'new-password',
            )
        )
        self.assertIsNone(vault_sessions.get(account_id))
        self.assertIsNone(
            await repository.get_by_email(
                str(account.email),
                'old-password',
            )
        )
        self.assertIsNotNone(
            await repository.get_by_email(
                str(account.email),
                'new-password',
            )
        )
        self.assertEqual(vault_sessions.get(account_id), original_umk)
        self.assertEqual(
            await get_account_llm_keys(account_id),
            {LLMProvider.ANTHROPIC: 'sk-test-anthropic'},
        )

    async def test_regenerating_umk_requires_confirmation_and_discards_keys(
        self,
    ) -> None:
        repository: SQLiteAccountRepository = SQLiteAccountRepository()
        account: Account = await repository.create(
            Account(
                name='Regeneration Owner',
                email='regeneration-owner@example.com',
            ),
            'account-password',
        )
        account_id = account.account_id or account.id
        await repository.get_by_email(
            str(account.email),
            'account-password',
        )
        previous_umk = vault_sessions.get(account_id)
        self.assertIsNotNone(previous_umk)
        assert previous_umk is not None
        await set_account_llm_key(
            account_id,
            LLMProvider.CHATGPT,
            'sk-test-openai',
        )

        with self.assertRaises(ValueError):
            await regenerate_account_umk(
                account_id,
                'account-password',
                confirmed=False,
            )
        self.assertEqual(
            await get_account_llm_keys(account_id),
            {LLMProvider.CHATGPT: 'sk-test-openai'},
        )

        self.assertTrue(
            await regenerate_account_umk(
                account_id,
                'account-password',
                confirmed=True,
            )
        )
        new_umk = vault_sessions.get(account_id)
        self.assertIsNotNone(new_umk)
        assert new_umk is not None
        self.assertNotEqual(new_umk, previous_umk)
        self.assertEqual(await get_account_llm_key_providers(account_id), [])
        self.assertEqual(await get_account_llm_keys(account_id), {})

    async def test_custom_report_is_saved_as_one_json_array_per_account(
        self,
    ) -> None:
        repository: SQLiteAccountRepository = SQLiteAccountRepository()
        account: Account = await repository.create(
            Account(
                name='Report Owner',
                email='report-owner@example.com',
                custom_report=['pe_ratio', 'roic'],
            ),
            'account-password',
        )
        account_id = account.account_id or account.id

        pool = await get_database_pool(
            self._database_path,
            auth_token=DB_AUTH_TOKEN,
            size=DB_POOL_SIZE,
            acquire_timeout=DB_POOL_TIMEOUT,
        )
        async with pool.connection() as connection:
            result = await connection.execute(
                '''
                SELECT account_id, custom_report_json
                FROM account_custom_reports
                WHERE account_id = ?
                ''',
                (str(account_id),),
            )
            rows = result.fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            json.loads(rows[0]['custom_report_json']),
            ['pe_ratio', 'roic'],
        )

        loaded_account = await account_storage.get_account_by_id(account_id)
        self.assertIsNotNone(loaded_account)
        self.assertEqual(loaded_account.custom_report, ['pe_ratio', 'roic'])
