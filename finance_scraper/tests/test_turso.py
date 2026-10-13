
import os
import pytest


# ================================================== #
# OPTIONAL REMOTE SMOKE TEST                         #
# ================================================== #

@pytest.mark.skipif(
    not os.getenv('TURSO_SMOKE_URL') or not os.getenv('TURSO_SMOKE_TOKEN'),
    reason='TURSO_SMOKE_URL and TURSO_SMOKE_TOKEN are required',
)
def test_turso_pipeline_smoke() -> None:
    """Run the remote smoke test only when explicitly requested."""

    import httpx

    response = httpx.post(
        f"{os.environ['TURSO_SMOKE_URL']}/v2/pipeline",
        headers={
            'Authorization': f"Bearer {os.environ['TURSO_SMOKE_TOKEN']}",
        },
        json={
            'requests': [
                {
                    'type': 'execute',
                    'stmt': {'sql': 'SELECT 1'},
                },
            ],
        },
        timeout=10,
    )
    response.raise_for_status()
