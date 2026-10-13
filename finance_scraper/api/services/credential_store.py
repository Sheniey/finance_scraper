import os

import keyring
from keyring.errors import KeyringError

from api.exceptions.google import CredentialStoreUnavailableError


_SERVICE_NAME: str = 'Finance Scraper'
_GOOGLE_REFRESH_TOKEN_PREFIX: str = 'google-refresh:'


def _require_windows_credential_manager() -> None:
    if os.name != 'nt':
        raise CredentialStoreUnavailableError()

    from keyring.backends.Windows import WinVaultKeyring

    if not isinstance(keyring.get_keyring(), WinVaultKeyring):
        raise CredentialStoreUnavailableError()


def store_google_refresh_token(account_id: str, token: str) -> None:
    _require_windows_credential_manager()
    try:
        keyring.set_password(
            _SERVICE_NAME,
            f'{_GOOGLE_REFRESH_TOKEN_PREFIX}{account_id}',
            token,
        )
    except (KeyringError, OSError) as e:
        raise CredentialStoreUnavailableError() from e


def get_google_refresh_token(account_id: str) -> str | None:
    _require_windows_credential_manager()
    try:
        return keyring.get_password(
            _SERVICE_NAME,
            f'{_GOOGLE_REFRESH_TOKEN_PREFIX}{account_id}',
        )
    except (KeyringError, OSError) as e:
        raise CredentialStoreUnavailableError() from e


def delete_google_refresh_token(account_id: str) -> bool:
    existing_token: str | None = get_google_refresh_token(account_id)
    if existing_token is None:
        return False

    try:
        keyring.delete_password(
            _SERVICE_NAME,
            f'{_GOOGLE_REFRESH_TOKEN_PREFIX}{account_id}',
        )
    except (KeyringError, OSError) as e:
        raise CredentialStoreUnavailableError() from e
    return True
