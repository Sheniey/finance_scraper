import json
import time
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from api.core.database import api_connection, api_transaction
from api.models.schedule import ReportSchedule
from api.schemas.schedule import ScheduleCreate


def _schedule_from_row(row: Mapping[str, Any]) -> ReportSchedule:
    tickers: object = json.loads(str(row['tickers_json']))
    if not isinstance(tickers, list) or not all(
        isinstance(ticker, str)
        for ticker in tickers
    ):
        raise ValueError('Stored schedule tickers must be a list of strings')
    return ReportSchedule(
        schedule_id=str(row['schedule_id']),
        account_id=str(row['account_id']),
        tickers=tuple(tickers),
        report_format=str(row['report_format']),
        run_at=str(row['run_at']),
        timezone=str(row['timezone']),
        explain=bool(row['explain']),
        mode=str(row['mode']),
        charts=bool(row['charts']),
        ml_horizon=int(row['ml_horizon']),
        enabled=bool(row['enabled']),
        last_run_date=(
            str(row['last_run_date'])
            if row['last_run_date'] is not None
            else None
        ),
        last_run_status=(
            str(row['last_run_status'])
            if row['last_run_status'] is not None
            else None
        ),
        last_error=(
            str(row['last_error'])
            if row['last_error'] is not None
            else None
        ),
        created_at=int(row['created_at']),
        updated_at=int(row['updated_at']),
    )


_SCHEDULE_SELECT: str = '''
    SELECT schedule_id, account_id, tickers_json, report_format, run_at,
        timezone, explain, mode, charts, ml_horizon, enabled, last_run_date,
        last_run_status, last_error, created_at, updated_at
    FROM api_schedules
'''


async def create_schedule(
    account_id: str,
    payload: ScheduleCreate,
) -> ReportSchedule:
    now: int = int(time.time())
    schedule_id: str = f'sch_{uuid4().hex}'
    async with api_transaction() as connection:
        await connection.execute(
            '''
            INSERT INTO api_schedules (
                schedule_id, account_id, tickers_json, report_format,
                run_at, timezone, explain, mode, charts, ml_horizon,
                enabled, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            ''',
            (
                schedule_id,
                account_id,
                json.dumps(payload.tickers, separators=(',', ':')),
                payload.report_format.value,
                payload.run_at.strftime('%H:%M'),
                payload.timezone,
                int(payload.explain),
                payload.mode.value,
                int(payload.charts),
                payload.ml_horizon,
                now,
                now,
            ),
        )
    schedule: ReportSchedule | None = await get_schedule(
        schedule_id,
        account_id,
    )
    if schedule is None:
        raise RuntimeError('Created schedule could not be read back')
    return schedule


async def get_schedule(
    schedule_id: str,
    account_id: str,
) -> ReportSchedule | None:
    async with api_connection() as connection:
        row = (
            await connection.execute(
                f'{_SCHEDULE_SELECT} '
                'WHERE schedule_id = ? AND account_id = ? LIMIT 1',
                (schedule_id, account_id),
            )
        ).fetchone()
    return _schedule_from_row(row) if row is not None else None


async def get_schedule_by_id(
    schedule_id: str,
) -> ReportSchedule | None:
    async with api_connection() as connection:
        row = (
            await connection.execute(
                f'{_SCHEDULE_SELECT} '
                'WHERE schedule_id = ? LIMIT 1',
                (schedule_id,),
            )
        ).fetchone()
    return _schedule_from_row(row) if row is not None else None


async def list_schedules(account_id: str) -> list[ReportSchedule]:
    async with api_connection() as connection:
        rows = (
            await connection.execute(
                f'{_SCHEDULE_SELECT} '
                'WHERE account_id = ? ORDER BY run_at, created_at',
                (account_id,),
            )
        ).fetchall()
    return [_schedule_from_row(row) for row in rows]


async def list_all_schedules() -> list[ReportSchedule]:
    async with api_connection() as connection:
        rows = (
            await connection.execute(
                f'{_SCHEDULE_SELECT} ORDER BY account_id, run_at, created_at',
            )
        ).fetchall()
    return [_schedule_from_row(row) for row in rows]


async def list_enabled_schedules() -> list[ReportSchedule]:
    async with api_connection() as connection:
        rows = (
            await connection.execute(
                f'{_SCHEDULE_SELECT} '
                'WHERE enabled = 1 ORDER BY run_at, created_at',
            )
        ).fetchall()
    return [_schedule_from_row(row) for row in rows]


async def count_schedules(account_id: str) -> int:
    async with api_connection() as connection:
        row = (
            await connection.execute(
                '''
                SELECT COUNT(*) AS schedule_count
                FROM api_schedules
                WHERE account_id = ?
                ''',
                (account_id,),
            )
        ).fetchone()
    return int(row['schedule_count']) if row is not None else 0


async def disable_account_schedules(account_id: str) -> list[str]:
    async with api_transaction() as connection:
        rows = (
            await connection.execute(
                '''
                SELECT schedule_id FROM api_schedules
                WHERE account_id = ? AND enabled = 1
                ''',
                (account_id,),
            )
        ).fetchall()
        schedule_ids: list[str] = [
            str(row['schedule_id'])
            for row in rows
        ]
        await connection.execute(
            '''
            UPDATE api_schedules
            SET enabled = 0, updated_at = ?
            WHERE account_id = ? AND enabled = 1
            ''',
            (int(time.time()), account_id),
        )
    return schedule_ids


async def delete_account_schedules(account_id: str) -> list[str]:
    async with api_transaction() as connection:
        rows = (
            await connection.execute(
                '''
                SELECT schedule_id FROM api_schedules
                WHERE account_id = ?
                ''',
                (account_id,),
            )
        ).fetchall()
        schedule_ids: list[str] = [
            str(row['schedule_id'])
            for row in rows
        ]
        await connection.execute(
            'DELETE FROM api_schedule_runs WHERE account_id = ?',
            (account_id,),
        )
        await connection.execute(
            'DELETE FROM api_schedules WHERE account_id = ?',
            (account_id,),
        )
    return schedule_ids


async def set_schedule_enabled(
    schedule_id: str,
    account_id: str,
    enabled: bool,
) -> ReportSchedule | None:
    now: int = int(time.time())
    async with api_transaction() as connection:
        await connection.execute(
            '''
            UPDATE api_schedules
            SET enabled = ?, updated_at = ?
            WHERE schedule_id = ? AND account_id = ?
            ''',
            (int(enabled), now, schedule_id, account_id),
        )
    return await get_schedule(schedule_id, account_id)


async def delete_schedule(schedule_id: str, account_id: str) -> bool:
    async with api_transaction() as connection:
        await connection.execute(
            '''
            DELETE FROM api_schedule_runs
            WHERE schedule_id = ? AND account_id = ?
            ''',
            (schedule_id, account_id),
        )
        result = await connection.execute(
            '''
            DELETE FROM api_schedules
            WHERE schedule_id = ? AND account_id = ?
            ''',
            (schedule_id, account_id),
        )
    return result.rowcount == 1


async def claim_schedule_run(
    schedule: ReportSchedule,
    scheduled_date: str,
) -> tuple[str, list[str], bool]:
    now: int = int(time.time())
    async with api_transaction() as connection:
        await connection.execute(
            '''
            INSERT OR IGNORE INTO api_schedule_runs (
                schedule_id, account_id, scheduled_date, status,
                report_ids_json, created_at, updated_at
            )
            VALUES (?, ?, ?, 'IN_PROGRESS', '[]', ?, ?)
            ''',
            (
                schedule.schedule_id,
                schedule.account_id,
                scheduled_date,
                now,
                now,
            ),
        )
        row = (
            await connection.execute(
                '''
                SELECT status, report_ids_json
                FROM api_schedule_runs
                WHERE schedule_id = ? AND scheduled_date = ?
                LIMIT 1
                ''',
                (schedule.schedule_id, scheduled_date),
            )
        ).fetchone()
        if row is None:
            raise RuntimeError('Schedule run could not be created')
        status: str = str(row['status'])
        report_ids_value: object = json.loads(str(row['report_ids_json']))
        if not isinstance(report_ids_value, list) or not all(
            isinstance(report_id, str)
            for report_id in report_ids_value
        ):
            raise ValueError('Stored schedule report IDs must be a list')
        report_ids: list[str] = report_ids_value
        if status in {'SENT', 'SENDING', 'DELIVERY_UNKNOWN'}:
            return status, report_ids, False
        if status == 'FAILED':
            await connection.execute(
                '''
                UPDATE api_schedule_runs
                SET status = 'IN_PROGRESS', error_code = NULL, updated_at = ?
                WHERE schedule_id = ? AND scheduled_date = ?
                ''',
                (now, schedule.schedule_id, scheduled_date),
            )
        return 'IN_PROGRESS', report_ids, True


async def update_schedule_run_reports(
    schedule_id: str,
    account_id: str,
    scheduled_date: str,
    report_ids: list[str],
) -> None:
    now: int = int(time.time())
    async with api_transaction() as connection:
        await connection.execute(
            '''
            UPDATE api_schedule_runs
            SET report_ids_json = ?, updated_at = ?
            WHERE schedule_id = ? AND account_id = ? AND scheduled_date = ?
            ''',
            (
                json.dumps(report_ids, separators=(',', ':')),
                now,
                schedule_id,
                account_id,
                scheduled_date,
            ),
        )


async def claim_schedule_delivery(
    schedule_id: str,
    account_id: str,
    scheduled_date: str,
) -> bool:
    now: int = int(time.time())
    async with api_transaction() as connection:
        result = await connection.execute(
            '''
            UPDATE api_schedule_runs
            SET status = 'SENDING', updated_at = ?
            WHERE schedule_id = ? AND account_id = ?
                AND scheduled_date = ? AND status = 'IN_PROGRESS'
            ''',
            (now, schedule_id, account_id, scheduled_date),
        )
    return result.rowcount == 1


async def finish_schedule_run(
    schedule_id: str,
    account_id: str,
    scheduled_date: str,
    status: str,
    *,
    error_code: str | None = None,
) -> None:
    now: int = int(time.time())
    async with api_transaction() as connection:
        await connection.execute(
            '''
            UPDATE api_schedule_runs
            SET status = ?, error_code = ?, updated_at = ?
            WHERE schedule_id = ? AND account_id = ? AND scheduled_date = ?
            ''',
            (
                status,
                error_code,
                now,
                schedule_id,
                account_id,
                scheduled_date,
            ),
        )
        await connection.execute(
            '''
            UPDATE api_schedules
            SET last_run_date = ?, last_run_status = ?, last_error = ?,
                updated_at = ?
            WHERE schedule_id = ? AND account_id = ?
            ''',
            (
                scheduled_date,
                status,
                error_code,
                now,
                schedule_id,
                account_id,
            ),
        )
