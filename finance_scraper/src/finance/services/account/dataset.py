"""Initial account dataset views backed by the Turso/libSQL account store."""


# ================================================== #
# MODULE: dataset
# ================================================== #

from finance.services.account.db import load_accounts
from finance.services.account.models import Account


async def load_dataset() -> tuple[
    list[Account],
    list[str],
    list[str],
    set[str],
]:
    """Load the optional dataset view on demand instead of during import."""

    accounts: list[Account] = await load_accounts()
    users: list[str] = [account.name for account in accounts]
    emails: list[str] = [str(account.email) for account in accounts]
    watchlist: set[str] = {
        item.symbol
        for account in accounts
        for item in account.watchlist
        if item is not None
    }
    return accounts, users, emails, watchlist


__all__: list[str] = ['load_dataset']
