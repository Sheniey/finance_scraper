from api.repositories import auth as AuthRepository


async def invalidate_tokens(
    *,
    session_id: str | None = None,
    account_id: str | None = None,
) -> None:
    if (session_id is None) == (account_id is None):
        raise ValueError('Provide exactly one session_id or account_id')
    if session_id is not None:
        await AuthRepository.revoke_session(session_id)
        return
    if account_id is None:
        raise ValueError('account_id is required')
    await AuthRepository.revoke_account_tokens(account_id)
