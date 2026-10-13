
from collections.abc import Awaitable, Callable
from fastapi import Depends

from finance.services.account import Account

from api.core.roles import Roles
from api.core.security import get_current_account
from api.exceptions.security import UnauthorizedError


def require_permission(
    permission: str,
) -> Callable[..., Awaitable[Account]]:
    async def dependency(
        account: Account = Depends(get_current_account),
    ) -> Account:
        role = Roles.get_role(account.role)
        if role is None or not role.has_permission(permission):
            raise UnauthorizedError(role)
        return account

    return dependency
