"""Background push and pull loop for the local Turso Sync replica."""

import asyncio, logging

from finance.services.database.exceptions import DatabaseSyncError
from finance.services.database.libsql import AsyncClientPool


logger: logging.Logger = logging.getLogger(__name__)
_SYNC_INTERVAL_SECONDS: float = 10.0


async def run_sync_worker(
    pool: AsyncClientPool,
    stop_event: asyncio.Event,
) -> None:
    """Push local CDC changes and pull remote changes until stopped."""

    while not stop_event.is_set():
        try:
            await pool.push()
            await pool.pull()
        except DatabaseSyncError as e:
            logger.warning(
                'Turso Sync is unavailable; local changes remain queued: %s',
                e,
            )

        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=_SYNC_INTERVAL_SECONDS,
            )
        except TimeoutError:
            continue
