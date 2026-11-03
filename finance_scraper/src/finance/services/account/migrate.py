"""Run the explicit local account database migration."""

import asyncio

from finance.services.account.db import migrate_account_schema


def main() -> None:
    """Migrate legacy account schemas and custom report storage when needed."""

    migrated: bool = asyncio.run(migrate_account_schema())
    if migrated:
        print(
            'Migrated the local account schema and preserved account data '
            'and relationships.'
        )
        return
    print('No local account schema migration was needed.')


if __name__ == '__main__':
    main()
