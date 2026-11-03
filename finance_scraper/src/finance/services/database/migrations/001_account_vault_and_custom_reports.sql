PRAGMA foreign_keys = ON;

BEGIN IMMEDIATE;

ALTER TABLE accounts
ADD COLUMN encrypted_umk TEXT;

ALTER TABLE account_custom_reports
RENAME TO account_custom_reports_legacy_v1;

CREATE TABLE account_custom_reports (
    account_id TEXT NOT NULL PRIMARY KEY
        REFERENCES accounts(account_id) ON DELETE CASCADE,
    custom_report_json TEXT NOT NULL
);

WITH serialized_reports AS (
    SELECT
        account_id,
        json_group_array(metric ORDER BY position) AS custom_report_json
    FROM account_custom_reports_legacy_v1
    GROUP BY account_id
)
INSERT INTO account_custom_reports (
    account_id, custom_report_json
)
SELECT accounts.account_id,
       COALESCE(serialized_reports.custom_report_json, '[]')
FROM accounts
LEFT JOIN serialized_reports
    ON serialized_reports.account_id = accounts.account_id;

CREATE TABLE account_llm_api_keys (
    account_id TEXT NOT NULL
        REFERENCES accounts(account_id) ON DELETE CASCADE,
    provider TEXT NOT NULL
        CHECK (provider IN ('deepseek', 'anthropic', 'chatgpt')),
    encrypted_value TEXT NOT NULL,
    PRIMARY KEY (account_id, provider)
);

DROP TABLE account_custom_reports_legacy_v1;

COMMIT;
