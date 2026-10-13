"""Profile a report with explicit cold-start or warm-request scenarios."""

import os
from pathlib import Path
from finance import Analyze



# ================================================== #
# PROFILE SCENARIO                                   #
# ================================================== #

Analyze(
    requested_symbol=os.getenv('PERF_TICKER', 'AAPL'),
    email=os.getenv('PERF_ACCOUNT_EMAIL'),
    password=os.getenv('PERF_ACCOUNT_PASSWORD'),
    mode=os.getenv('PERF_MODE', 'full'),
    to=os.getenv('PERF_OUTPUT', 'testing_reports/{ticker}/{date}.pdf'),
    ml_horizon=int(os.getenv('PERF_HORIZON', '60')),
    verbose=False,
)
