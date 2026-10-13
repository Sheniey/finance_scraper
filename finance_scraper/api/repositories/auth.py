
import time

from finance.services.database import AsyncDatabaseTransaction

from api.core.database import api_connection, api_transaction


async def store_token_pair(
    *,
    session_id: str,
    account_id: str,
    access_jti: str,
    access_expires_at: int,
    refresh_jti: str,
    refresh_expires_at: int,
    issued_at: int,
) -> None:
    async with api_transaction() as connection:
        await _insert_token(
            connection,
            token_id=access_jti,
            session_id=session_id,
            account_id=account_id,
            token_type='access',
            issued_at=issued_at,
            expires_at=access_expires_at,
        )
        await _insert_token(
            connection,
            token_id=refresh_jti,
            session_id=session_id,
            account_id=account_id,
            token_type='refresh',
            issued_at=issued_at,
            expires_at=refresh_expires_at,
        )

async def _insert_token(
    connection: AsyncDatabaseTransaction,
    *,
    token_id: str,
    session_id: str,
    account_id: str,
    token_type: str,
    issued_at: int,
    expires_at: int,
) -> None:
    await connection.execute(
        '''
        INSERT INTO api_tokens (
            jti, session_id, account_id, token_type, issued_at, expires_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ''',
        (
            token_id,
            session_id,
            account_id,
            token_type,
            issued_at,
            expires_at,
        ),
    )

async def is_token_active(
    *,
    token_id: str,
    session_id: str,
    account_id: str,
    token_type: str,
    now: int | None = None,
) -> bool:
    checked_at: int = now if now is not None else int(time.time())
    async with api_connection() as connection:
        row = (
            await connection.execute(
                '''
                SELECT 1
                FROM api_tokens
                WHERE jti = ?
                    AND session_id = ?
                    AND account_id = ?
                    AND token_type = ?
                    AND revoked_at IS NULL
                    AND expires_at > ?
                LIMIT 1
                ''',
                (
                    token_id,
                    session_id,
                    account_id,
                    token_type,
                    checked_at,
                ),
            )
        ).fetchone()
    return row is not None

async def rotate_refresh_token(
    *,
    old_refresh_jti: str,
    session_id: str,
    account_id: str,
    new_access_jti: str,
    access_expires_at: int,
    new_refresh_jti: str,
    refresh_expires_at: int,
    issued_at: int,
) -> bool:
    async with api_transaction() as connection:
        old_token = (
            await connection.execute(
                '''
                SELECT account_id, token_type, revoked_at, expires_at
                FROM api_tokens
                WHERE jti = ? AND session_id = ?
                LIMIT 1
                ''',
                (old_refresh_jti, session_id),
            )
        ).fetchone()
        if (
            old_token is None
            or old_token['account_id'] != account_id
            or old_token['token_type'] != 'refresh'
            or int(old_token['expires_at']) <= issued_at
        ):
            return False

        if old_token['revoked_at'] is not None:
            await connection.execute(
                '''
                UPDATE api_tokens
                SET revoked_at = COALESCE(revoked_at, ?)
                WHERE session_id = ?
                ''',
                (issued_at, session_id),
            )
            return False

        updated = await connection.execute(
            '''
            UPDATE api_tokens
            SET revoked_at = ?
            WHERE jti = ? AND revoked_at IS NULL
            ''',
            (issued_at, old_refresh_jti),
        )
        if updated.rowcount != 1:
            return False

        await _insert_token(
            connection,
            token_id=new_access_jti,
            session_id=session_id,
            account_id=account_id,
            token_type='access',
            issued_at=issued_at,
            expires_at=access_expires_at,
        )
        await _insert_token(
            connection,
            token_id=new_refresh_jti,
            session_id=session_id,
            account_id=account_id,
            token_type='refresh',
            issued_at=issued_at,
            expires_at=refresh_expires_at,
        )
    return True

async def revoke_session(session_id: str, *, revoked_at: int | None = None) -> None:
    timestamp: int = revoked_at if revoked_at is not None else int(time.time())
    async with api_transaction() as connection:
        await connection.execute(
            '''
            UPDATE api_tokens
            SET revoked_at = COALESCE(revoked_at, ?)
            WHERE session_id = ?
            ''',
            (timestamp, session_id),
        )

async def revoke_account_tokens(
    account_id: str,
    *,
    revoked_at: int | None = None,
) -> None:
    timestamp: int = revoked_at if revoked_at is not None else int(time.time())
    async with api_transaction() as connection:
        await connection.execute(
            '''
            UPDATE api_tokens
            SET revoked_at = COALESCE(revoked_at, ?)
            WHERE account_id = ?
            ''',
            (timestamp, account_id),
        )
