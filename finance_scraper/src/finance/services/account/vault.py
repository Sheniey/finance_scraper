"""Versioned encryption for account-owned language-model credentials."""

import base64, binascii
import json, secrets
from enum import StrEnum
from threading import RLock
from typing import Any, Final as Const
from uuid import UUID

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from finance.config import APP_NAME_CODING_2
from finance.services.account.exceptions import (
    VaultEnvelopeError,
    VaultAuthenticationError
)


# ================================================== #
# SETUP INFO                                         #
# ================================================== #

_UMK_SIZE: Const[int] = 32
_SALT_SIZE: Const[int] = 16
_NONCE_SIZE: Const[int] = 12
_ARGON2_TIME_COST: Const[int] = 3
_ARGON2_MEMORY_COST_KIB: Const[int] = 65_536
_ARGON2_PARALLELISM: Const[int] = 1
_ENVELOPE_VERSION: Const[int] = 1
_CIPHER_NAME: Const[str] = 'AES-256-GCM'
_KDF_NAME: Const[str] = 'argon2id'


# ================================================== #
# ENUMERATIONS                                       #
# ================================================== #

class LLMProvider(StrEnum): # maybe ts not should be here
    """Supported account-owned language-model providers."""

    DEEPSEEK = 'deepseek'
    ANTHROPIC = 'anthropic'
    CHATGPT = 'chatgpt'


# ================================================== #
# HELPER FUNCTIONS                                   #
# ================================================== #

def _account_id_text(account_id: UUID | str) -> str:
    try:
        return str(UUID(str(account_id)))
    except (TypeError, ValueError) as e:
        raise ValueError('A valid account UUID is required.') from e

def _umk_aad(account_id: UUID | str) -> bytes:
    return (
        f'{APP_NAME_CODING_2}:umk:v{_ENVELOPE_VERSION}:'
        f'{_account_id_text(account_id)}'
    ).encode('ascii')

def _provider_key_aad(account_id: UUID | str, provider: LLMProvider) -> bytes:
    return (
        f'{APP_NAME_CODING_2}:llm-key:v{_ENVELOPE_VERSION}:'
        f'{_account_id_text(account_id)}:{provider.value}'
    ).encode('ascii')

def _derive_wrapping_key(password: str, salt: bytes) -> bytes:
    if not isinstance(password, str) or not password:
        raise ValueError('An account password is required to unlock the vault.')
    
    return hash_secret_raw(
        secret=password.encode('utf-8'),
        salt=salt,
        time_cost=_ARGON2_TIME_COST,
        memory_cost=_ARGON2_MEMORY_COST_KIB,
        parallelism=_ARGON2_PARALLELISM,
        hash_len=_UMK_SIZE,
        type=Type.ID,
    )

def _encode_bytes(value: bytes) -> str:
    return base64.b64encode(value).decode('ascii')

def _decode_bytes(payload: dict[str, Any], field_name: str, *, expected_size: int | None = None) -> bytes:
    value: Any = payload.get(field_name)
    if not isinstance(value, str):
        raise VaultEnvelopeError(
            f'The encrypted vault is missing {field_name!r}.',
        )

    try:
        decoded_value: bytes = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as e:
        raise VaultEnvelopeError(f'The encrypted vault contains invalid {field_name!r}.',) from e
    
    if expected_size is not None and len(decoded_value) != expected_size:
        raise VaultEnvelopeError(f'The encrypted vault contains invalid {field_name!r}.',)
    return decoded_value

def _parse_envelope(envelope: str) -> dict[str, Any]:
    if not isinstance(envelope, str) or not envelope:
        raise VaultEnvelopeError('The encrypted vault envelope is empty.')
    
    try:
        payload: Any = json.loads(envelope)
    except json.JSONDecodeError as e:
        raise VaultEnvelopeError('The encrypted vault envelope is not valid JSON.') from e
    
    if not isinstance(payload, dict):
        raise VaultEnvelopeError('The encrypted vault envelope must be a JSON object.')
    
    if (
        payload.get('version') != _ENVELOPE_VERSION
        or payload.get('cipher') != _CIPHER_NAME
    ):
        raise VaultEnvelopeError('The encrypted vault envelope version is not supported.')
    return payload


# ================================================== #
# UTILITIES                                          #
# ================================================== #

def normalize_llm_provider(provider: str | LLMProvider) -> LLMProvider:
    """Normalize and validate a provider identifier."""

    if isinstance(provider, LLMProvider):
        return provider

    normalized_provider: str = provider.strip().casefold()
    if normalized_provider == 'openai':
        normalized_provider = LLMProvider.CHATGPT.value

    try:
        return LLMProvider(normalized_provider)
    except ValueError as e:
        raise ValueError(f'Unsupported LLM provider: {provider!r}.') from e

def generate_umk() -> bytes:
    """Generate a random 256-bit user master key."""
    return secrets.token_bytes(_UMK_SIZE)

def wrap_umk(
    umk: bytes,
    password: str,
    account_id: UUID | str
) -> str:
    """Encrypt a UMK with a password-derived Argon2id wrapping key."""

    if len(umk) != _UMK_SIZE:
        raise ValueError('The UMK must contain exactly 32 bytes.')

    salt: bytes = secrets.token_bytes(_SALT_SIZE)
    nonce: bytes = secrets.token_bytes(_NONCE_SIZE)
    wrapping_key: bytes = _derive_wrapping_key(password, salt)
    ciphertext: bytes = AESGCM(wrapping_key).encrypt(
        nonce,
        umk,
        _umk_aad(account_id),
    )
    envelope: dict[str, Any] = {
        'version': _ENVELOPE_VERSION,
        'cipher': _CIPHER_NAME,
        'kdf': {
            'name': _KDF_NAME,
            'time_cost': _ARGON2_TIME_COST,
            'memory_cost_kib': _ARGON2_MEMORY_COST_KIB,
            'parallelism': _ARGON2_PARALLELISM,
        },
        'salt': _encode_bytes(salt),
        'nonce': _encode_bytes(nonce),
        'ciphertext': _encode_bytes(ciphertext),
    }
    return json.dumps(envelope, separators=(',', ':'), sort_keys=True)

def unwrap_umk(
    envelope: str,
    password: str,
    account_id: UUID | str
) -> bytes:
    """Decrypt a UMK using the account password and its account-bound AAD."""

    payload: dict[str, Any] = _parse_envelope(envelope)
    kdf: Any = payload.get('kdf')
    expected_kdf: dict[str, Any] = {
        'name': _KDF_NAME,
        'time_cost': _ARGON2_TIME_COST,
        'memory_cost_kib': _ARGON2_MEMORY_COST_KIB,
        'parallelism': _ARGON2_PARALLELISM,
    }
    if kdf != expected_kdf:
        raise VaultEnvelopeError(
            'The encrypted vault KDF parameters are not supported.',
        )

    salt: bytes = _decode_bytes(
        payload,
        'salt',
        expected_size=_SALT_SIZE,
    )
    nonce: bytes = _decode_bytes(
        payload,
        'nonce',
        expected_size=_NONCE_SIZE,
    )
    ciphertext: bytes = _decode_bytes(payload, 'ciphertext')
    wrapping_key: bytes = _derive_wrapping_key(password, salt)
    try:
        umk: bytes = AESGCM(wrapping_key).decrypt(
            nonce,
            ciphertext,
            _umk_aad(account_id),
        )
    except InvalidTag as e:
        raise VaultAuthenticationError(
            'The account password or vault data is invalid.',
        ) from e
    
    if len(umk) != _UMK_SIZE:
        raise VaultEnvelopeError('The decrypted UMK has an invalid length.')
    return umk

def encrypt_provider_key(
    api_key: str,
    umk: bytes,
    account_id: UUID | str,
    provider: str | LLMProvider
) -> str:
    """Encrypt a provider API key with account/provider-bound AAD."""

    normalized_provider: LLMProvider = normalize_llm_provider(provider)
    if len(umk) != _UMK_SIZE:
        raise ValueError('The UMK must contain exactly 32 bytes.')
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError('A non-empty provider API key is required.')

    nonce: bytes = secrets.token_bytes(_NONCE_SIZE)
    ciphertext: bytes = AESGCM(umk).encrypt(
        nonce,
        api_key.strip().encode('utf-8'),
        _provider_key_aad(account_id, normalized_provider),
    )
    envelope: dict[str, Any] = {
        'version': _ENVELOPE_VERSION,
        'cipher': _CIPHER_NAME,
        'nonce': _encode_bytes(nonce),
        'ciphertext': _encode_bytes(ciphertext),
    }
    return json.dumps(envelope, separators=(',', ':'), sort_keys=True)

def decrypt_provider_key(
    envelope: str,
    umk: bytes,
    account_id: UUID | str,
    provider: str | LLMProvider
) -> str:
    """Decrypt a provider API key bound to the requested account/provider."""
    normalized_provider: LLMProvider = normalize_llm_provider(provider)
    if len(umk) != _UMK_SIZE:
        raise ValueError('The UMK must contain exactly 32 bytes.')
    
    payload: dict[str, Any] = _parse_envelope(envelope)
    nonce: bytes = _decode_bytes(
        payload,
        'nonce',
        expected_size=_NONCE_SIZE,
    )

    ciphertext: bytes = _decode_bytes(payload, 'ciphertext')
    try:
        plaintext: bytes = AESGCM(umk).decrypt(
            nonce,
            ciphertext,
            _provider_key_aad(account_id, normalized_provider),
        )
    except InvalidTag as e:
        raise VaultAuthenticationError('The provider key or vault data is invalid.') from e
    
    try:
        return plaintext.decode('utf-8')
    except UnicodeDecodeError as e:
        raise VaultEnvelopeError('The decrypted provider key is not valid UTF-8.') from e



# ================================================== #
# REPOSITORY                                         #
# ================================================== #

class VaultSessionCache:
    """Keep unlocked UMKs in process memory without persisting them."""

    def __init__(self) -> None:
        self.__umks: dict[str, bytes] = {}
        self.__lock: RLock = RLock()

    def unlock(self, account_id: UUID | str, umk: bytes) -> None:
        if len(umk) != _UMK_SIZE:
            raise ValueError('The UMK must contain exactly 32 bytes.')
        account_id_text: str = _account_id_text(account_id)
        with self.__lock:
            self.__umks[account_id_text] = bytes(umk)

    def get(self, account_id: UUID | str) -> bytes | None:
        account_id_text: str = _account_id_text(account_id)
        with self.__lock:
            return self.__umks.get(account_id_text)

    def lock(self, account_id: UUID | str) -> None:
        account_id_text: str = _account_id_text(account_id)
        with self.__lock:
            self.__umks.pop(account_id_text, None)

    def clear(self) -> None:
        with self.__lock:
            self.__umks.clear()


vault_sessions: Const[VaultSessionCache] = VaultSessionCache()
