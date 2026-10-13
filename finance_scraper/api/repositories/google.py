import json
import time

from api.core.database import api_connection, api_transaction
from api.models.google import GoogleAccountConnection


async def save_google_connection(
    account_id: str,
    google_email: str,
    scopes: tuple[str, ...],
    *,
    connected_at: int | None = None,
) -> GoogleAccountConnection:
    now: int = int(time.time())
    established_at: int = connected_at if connected_at is not None else now
    async with api_transaction() as connection:
        await connection.execute(
            '''
            INSERT INTO api_google_accounts (
                account_id, google_email, scopes_json, connected_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(account_id) DO UPDATE SET
                google_email = excluded.google_email,
                scopes_json = excluded.scopes_json,
                updated_at = excluded.updated_at
            ''',
            (
                account_id,
                google_email,
                json.dumps(scopes, separators=(',', ':')),
                established_at,
                now,
            ),
        )
    return GoogleAccountConnection(
        account_id=account_id,
        google_email=google_email,
        scopes=scopes,
        connected_at=established_at,
        updated_at=now,
    )


async def get_google_connection(
    account_id: str,
) -> GoogleAccountConnection | None:
    async with api_connection() as connection:
        row = (
            await connection.execute(
                '''
                SELECT account_id, google_email, scopes_json,
                    connected_at, updated_at
                FROM api_google_accounts
                WHERE account_id = ?
                LIMIT 1
                ''',
                (account_id,),
            )
        ).fetchone()
    if row is None:
        return None
    scopes: object = json.loads(str(row['scopes_json']))
    if not isinstance(scopes, list) or not all(
        isinstance(scope, str)
        for scope in scopes
    ):
        raise ValueError('Stored Google scopes must be a list of strings')
    return GoogleAccountConnection(
        account_id=str(row['account_id']),
        google_email=str(row['google_email']),
        scopes=tuple(scopes),
        connected_at=int(row['connected_at']),
        updated_at=int(row['updated_at']),
    )


async def delete_google_connection(account_id: str) -> bool:
    async with api_transaction() as connection:
        result = await connection.execute(
            'DELETE FROM api_google_accounts WHERE account_id = ?',
            (account_id,),
        )
    return result.rowcount > 0
