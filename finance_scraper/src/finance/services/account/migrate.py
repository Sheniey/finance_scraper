"""
Run the explicit account database migration before application startup.
"""

import asyncio

from finance.services.account.db import migrate_account_schema


def main() -> None:
    """Migrate legacy integer account IDs to UUIDs when needed."""

    migrated: bool = asyncio.run(migrate_account_schema())
    if migrated:
        print(
            'Migrated account IDs to UUIDs and preserved account data '
            'and relationships.'
        )
        return
    print('No legacy integer account schema found; no migration was needed.')


if __name__ == '__main__':
    main()
