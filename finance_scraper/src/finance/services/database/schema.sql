CREATE TABLE IF NOT EXISTS languages (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tickers (
    ticker_id INTEGER PRIMARY KEY,
    ticker TEXT NOT NULL,
    region TEXT NOT NULL,
    UNIQUE (ticker, region)
);

CREATE TABLE IF NOT EXISTS currencies (
    currency_id INTEGER PRIMARY KEY,
    currency TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT NOT NULL PRIMARY KEY,
    email TEXT NOT NULL COLLATE NOCASE UNIQUE,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    language_code TEXT NOT NULL REFERENCES languages(code),
    language_style TEXT NOT NULL
        CHECK (language_style IN ('friendly', 'professional', 'technical')),
    password_hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_accounts_name_nocase
ON accounts (name COLLATE NOCASE);

CREATE TABLE IF NOT EXISTS action_history (
    action_id INTEGER PRIMARY KEY,
    account_id TEXT NOT NULL
        REFERENCES accounts(account_id) ON DELETE CASCADE,
    ticker_id INTEGER NOT NULL REFERENCES tickers(ticker_id),
    currency_id INTEGER NOT NULL REFERENCES currencies(currency_id),
    action TEXT NOT NULL CHECK (action IN ('BUY', 'SELL')),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price REAL NOT NULL CHECK (price >= 0),
    timestamp DATETIME NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_action_history_account_action
ON action_history (account_id, action_id);

CREATE TABLE IF NOT EXISTS account_custom_reports (
    account_id TEXT NOT NULL
        REFERENCES accounts(account_id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    metric TEXT NOT NULL,
    PRIMARY KEY (account_id, position)
);

CREATE TABLE IF NOT EXISTS account_watchlist (
    account_id TEXT NOT NULL
        REFERENCES accounts(account_id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position >= 0),
    is_empty INTEGER NOT NULL DEFAULT 0 CHECK (is_empty IN (0, 1)),
    ticker_id INTEGER REFERENCES tickers(ticker_id),
    rendering_mode TEXT NOT NULL DEFAULT 'classic'
        CHECK (
            rendering_mode IN (
                'classic',
                'full',
                'custom',
                'growth',
                'validation',
                'info'
            )
        ),
    llm_explanation INTEGER NOT NULL DEFAULT 0
        CHECK (llm_explanation IN (0, 1)),
    PRIMARY KEY (account_id, position),
    CHECK (
        (is_empty = 1 AND ticker_id IS NULL)
        OR (is_empty = 0 AND ticker_id IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS report_jobs (
    report_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    resource TEXT NOT NULL,
    request_json TEXT NOT NULL,
    status TEXT NOT NULL
        CHECK (status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED')),
    filename TEXT NOT NULL,
    report_format TEXT NOT NULL,
    content_type TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    artifact BLOB,
    cache_key TEXT,
    is_personalized INTEGER NOT NULL DEFAULT 0
        CHECK (is_personalized IN (0, 1)),
    source TEXT NOT NULL DEFAULT 'api',
    error_code TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    started_at INTEGER,
    completed_at INTEGER,
    expires_at INTEGER,
    worker_id TEXT,
    lease_until INTEGER,
    CHECK (status != 'COMPLETED' OR artifact IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_report_jobs_queue
ON report_jobs (status, lease_until, created_at);

CREATE INDEX IF NOT EXISTS idx_report_jobs_owner
ON report_jobs (account_id, created_at);

CREATE INDEX IF NOT EXISTS idx_report_jobs_expiry
ON report_jobs (expires_at, status);

CREATE TABLE IF NOT EXISTS report_store_migrations (
    source_database TEXT PRIMARY KEY,
    completed_at INTEGER NOT NULL
);
