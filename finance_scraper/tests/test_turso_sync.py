import subprocess
import sys
from pathlib import Path

import pytest

from finance.services.database.exceptions import (
    DatabaseConfigurationError,
)
from finance.services.database.sync import (
    acquire_sync_file_lock,
    validate_sync_url,
)


@pytest.mark.parametrize(
    ('remote_url', 'expected'),
    [
        ('turso://financescraper-sheniey.turso.io', True),
        ('https://financescraper-sheniey.turso.io', True),
        ('libsql://financescraper-sheniey.turso.io', False),
        ('http://financescraper-sheniey.turso.io', False),
        ('https://token@financescraper-sheniey.turso.io', False),
        ('https://financescraper-sheniey.turso.io?authToken=secret', False),
        ('', False),
    ],
)
def test_validate_turso_sync_url(remote_url: str, expected: bool) -> None:
    if not expected:
        with pytest.raises(DatabaseConfigurationError):
            validate_sync_url(remote_url)
        return

    assert validate_sync_url(remote_url) == remote_url


def test_file_lock_rejects_a_second_process(tmp_path: Path) -> None:
    database_path: Path = tmp_path / 'financescraper.sqlite3'
    file_lock = acquire_sync_file_lock(database_path)
    code: str = (
        'import sys\n'
        'from finance.services.database.exceptions import '
        'DatabaseAlreadyOpenError\n'
        'from finance.services.database.sync import acquire_sync_file_lock\n'
        'try:\n'
        '    acquire_sync_file_lock(sys.argv[1])\n'
        'except DatabaseAlreadyOpenError:\n'
        "    print('blocked')\n"
        'else:\n'
        '    raise SystemExit(2)\n'
    )
    try:
        result = subprocess.run(
            [sys.executable, '-c', code, str(database_path)],
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )
    finally:
        file_lock.release()

    assert result.returncode == 0
    assert result.stdout.strip() == 'blocked'

    reopened_lock = acquire_sync_file_lock(database_path)
    reopened_lock.release()
