
from api.models.role import Role

class Roles:
    GUEST: Role = Role(
        name='guest',
        permissions=frozenset(
            {
                'account:create',
                'report:limited-read',
                'report:info'
            }
        ),
    )
    "He/She only can CREATE a new account or READ all reports as limited read."
    USER: Role = Role(
        name='user',
        permissions=frozenset(
            {
                'auth:login',
                'auth:logout',
                'auth:refresh',
                'account-me:read',
                'account-me:update',
                'account-me:delete',
                'account-me:change-password',
                'report:limited-read',
                'report:create',
                'report:info',
                'report-me:read',
                'report-me:delete',
            },
        ),
    )
    "He/She can't ACCESS to all accounts and reports (only limited READ), just their own."
    TESTER: Role = Role(
        name='tester',
        permissions=frozenset(
            {
                'auth:login',
                'auth:logout',
                'auth:refresh',
                'account:read',
                'account:create',
                'account:update',
                'account-me:read',
                'account-me:update',
                'report:limited-read',
                'report:read',
                'report:info',
                'report:create',
                'report-me:read',
                'report-me:delete',
            },
        ),
    )
    "He/She can't DELETE their own account or all accounts."
    ADMIN: Role = Role(
        name='admin',
        permissions=frozenset({'everything'}),
    )
    "He/She has all permissions."

    _roles: dict[str, Role] = {
        GUEST.name: GUEST,
        USER.name: USER,
        TESTER.name: TESTER,
        ADMIN.name: ADMIN,
    }

    @classmethod
    def get_role(cls, name: str) -> Role | None:
        return cls._roles.get(name)

    @classmethod
    def all_roles(cls) -> list[Role]:
        return list(cls._roles.values())
